import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CoursePublishPage from '../src/pages/dosen/ai/CoursePublishPage';
import * as coursePlanService from '../src/services/coursePlanService';
import * as moodleIntegrationService from '../src/services/moodleIntegrationService';
import * as executionService from '../src/services/executionService';
import * as workflowService from '../src/services/workflowService';
import { ApiError } from '../src/services/apiClient';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockUseCourse = vi.fn();
vi.mock('../src/hooks/useCourse', () => ({
  useCourse: () => mockUseCourse(),
}));

describe('FE-13.1 Moodle Structure Execution Readiness Check & Start', () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);

    mockUseCourse.mockReturnValue({
      course: { id: 'course-1', name: 'Basis Data', fullname: 'Basis Data (Contoh)' },
      moodleCourse: { id: 2, fullname: 'Basis Data (Contoh)', shortname: 'IF2230-SAMPLE' },
      workflow: { id: 'wf-1', moodle_course_id: 2, status: 'RUNNING' },
      workflowId: 'wf-1',
      refresh: vi.fn(),
    });

    vi.spyOn(coursePlanService, 'getWorkflowPlan').mockResolvedValue({
      id: 'plan-1',
      version: 1,
      status: 'APPROVED',
      weeks: Array.from({ length: 16 }, (_, i) => ({ week_number: i + 1, title: `Minggu ${i + 1}` })),
    });

    vi.spyOn(moodleIntegrationService, 'getMoodleStatus').mockResolvedValue({
      status: 'CONNECTED',
      connected: true,
      site_name: 'Moodle Dev ITK',
      release: '4.5+ (Build: 20261001)',
    });

    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([]);
    vi.spyOn(executionService, 'startExecution').mockResolvedValue({
      execution_id: 'exec-demo-1',
      workflow_id: 'wf-1',
      scope: 'STRUCTURE',
      status: 'PENDING',
      moodle_course_id: 2,
      summary: { total: 16, success: 0, failed: 0, skipped: 0 },
    });
  });

  afterEach(() => {
    act(() => root?.unmount());
    root = null;
    container.remove();
    vi.restoreAllMocks();
  });

  async function renderPage() {
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={['/course/2/ai/publish']}>
          <Routes>
            <Route path="/course/:id/ai/publish" element={<CoursePublishPage />} />
          </Routes>
        </MemoryRouter>
      );
    });
  }

  async function waitFor(check, label, timeout = 3000) {
    const start = Date.now();
    while (!check()) {
      if (Date.now() - start > timeout) {
        throw new Error(`Timeout: ${label}. Isi: ${container.textContent.slice(0, 400)}`);
      }
      await act(() => new Promise((r) => setTimeout(r, 20)));
    }
  }

  it('menampilkan seluruh checklist prasyarat dan mengaktifkan tombol eksekusi bila semua siap', async () => {
    await renderPage();
    await waitFor(() => container.textContent.includes('Kesiapan Eksekusi Struktur Course'), 'Readiness card');

    // Seluruh prasyarat harus tampil
    expect(container.textContent).toContain('Course Plan Disetujui');
    expect(container.textContent).toContain('Target Kursus Moodle');
    expect(container.textContent).toContain('Koneksi Server Moodle');
    expect(container.textContent).toContain('Disetujui (Versi 1)');
    expect(container.textContent).toContain('Terhubung (#2)');
    expect(container.textContent).toContain('Semua prasyarat terpenuhi');

    // Tombol eksekusi harus aktif
    const button = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Eksekusi Struktur Course')
    );
    expect(button).toBeTruthy();
    expect(button.disabled).toBe(false);
  });

  it('menonaktifkan tombol eksekusi dan memberi tautan ke Rencana bila Course Plan belum APPROVED', async () => {
    vi.spyOn(coursePlanService, 'getWorkflowPlan').mockResolvedValue({
      id: 'plan-1',
      version: 1,
      status: 'DRAFT',
      weeks: [{ week_number: 1, title: 'Minggu 1' }],
    });

    await renderPage();
    await waitFor(() => container.textContent.includes('Draft (Menunggu Persetujuan)'), 'Draft plan status');

    // Tombol eksekusi harus dinonaktifkan
    const button = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Eksekusi Struktur Course')
    );
    expect(button.disabled).toBe(true);

    // Harus ada tautan perbaikan cepat ke tab Rencana
    const planLink = [...container.querySelectorAll('a')].find((a) =>
      a.textContent.includes('Buka Tab Rencana →')
    );
    expect(planLink).toBeTruthy();
    expect(planLink.getAttribute('href')).toContain('/plan');
  });

  it('menonaktifkan tombol eksekusi dan memberi tautan bila Target Kursus Moodle belum dipilih', async () => {
    mockUseCourse.mockReturnValue({
      course: { id: 'course-1', name: 'Basis Data' },
      moodleCourse: null,
      workflow: { id: 'wf-1', moodle_course_id: null, status: 'RUNNING' },
      workflowId: 'wf-1',
      refresh: vi.fn(),
    });

    await renderPage();
    await waitFor(() => container.textContent.includes('Belum Dipilih'), 'Target belum dipilih');

    const button = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Eksekusi Struktur Course')
    );
    expect(button.disabled).toBe(true);

    // Harus ada tautan perbaikan cepat ke tab Target
    const targetLink = [...container.querySelectorAll('a')].find((a) =>
      a.textContent.includes('Pilih Target Kursus →')
    );
    expect(targetLink).toBeTruthy();
    expect(targetLink.getAttribute('href')).toContain('/target');
  });

  it('menonaktifkan tombol eksekusi bila server Moodle terputus', async () => {
    vi.spyOn(moodleIntegrationService, 'getMoodleStatus').mockResolvedValue({
      status: 'DISCONNECTED',
      connected: false,
      message: 'Connection timed out to Moodle gateway.',
    });

    await renderPage();
    await waitFor(() => container.textContent.includes('Terputus'), 'Moodle terputus');

    const button = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Eksekusi Struktur Course')
    );
    expect(button.disabled).toBe(true);
    expect(container.textContent).toContain('Connection timed out to Moodle gateway.');
  });

  it('membuka modal konfirmasi dan berhasil memanggil startExecution saat dikonfirmasi', async () => {
    await renderPage();
    await waitFor(() => container.textContent.includes('Eksekusi Struktur Course'), 'Ready button');

    const startBtn = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Eksekusi Struktur Course')
    );

    // Klik tombol eksekusi -> muncul modal konfirmasi
    await act(async () => {
      startBtn.click();
    });

    await waitFor(() => container.querySelector('dialog'), 'Modal konfirmasi');
    expect(container.querySelector('dialog').textContent).toContain('Konfirmasi Eksekusi Struktur Course');
    expect(container.querySelector('dialog').textContent).toContain('16 section mingguan');
    expect(container.querySelector('dialog').textContent).toContain('idempotent');

    // Klik konfirmasi "Ya, Mulai Eksekusi"
    const confirmBtn = [...container.querySelectorAll('dialog button')].find((b) =>
      b.textContent.includes('Ya, Mulai Eksekusi')
    );
    expect(confirmBtn).toBeTruthy();

    await act(async () => {
      confirmBtn.click();
    });

    // startExecution harus dipanggil dengan workflowId dan scope "STRUCTURE"
    expect(executionService.startExecution).toHaveBeenCalledWith('wf-1', 'STRUCTURE');

    // Dialog menutup dan status eksekusi baru tampil di halaman
    await waitFor(() => container.textContent.includes('Status Eksekusi Struktur Moodle'), 'Status eksekusi');
    expect(container.textContent).toContain('PENDING');
    expect(container.textContent).toContain('exec-demo-1');
  });

  it('menampilkan pesan penolakan server 409 sesuai kode alasan (EXECUTION_IN_PROGRESS)', async () => {
    const error409 = new ApiError('INVALID_REQUEST', 409, 'Eksekusi sedang berjalan.', [
      { field: 'reason', message: 'EXECUTION_IN_PROGRESS' },
    ]);
    vi.spyOn(executionService, 'startExecution').mockRejectedValue(error409);

    await renderPage();
    await waitFor(() => container.textContent.includes('Eksekusi Struktur Course'), 'Ready button');

    const startBtn = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Eksekusi Struktur Course')
    );
    await act(async () => {
      startBtn.click();
    });

    const confirmBtn = [...container.querySelectorAll('dialog button')].find((b) =>
      b.textContent.includes('Ya, Mulai Eksekusi')
    );
    await act(async () => {
      confirmBtn.click();
    });

    // Pesan error terjemahan ramah pengguna harus muncul
    await waitFor(() => container.textContent.includes('Eksekusi struktur lain sedang berjalan'), 'Error alert');
    expect(container.textContent).toContain('Eksekusi struktur lain sedang berjalan pada alur kerja ini.');
  });

  it('otomatis mengikat moodle_course_id sebelum startExecution bila workflow server belum terikat', async () => {
    mockUseCourse.mockReturnValue({
      course: { id: 'course-1', name: 'Sistem Basis Data' },
      moodleCourse: { id: 48, fullname: 'Sistem Basis Data', shortname: 'SBD-2223' },
      workflow: { id: 'wf-1', moodle_course_id: null, status: 'RUNNING', rps_id: 'rps-1' },
      workflowId: 'wf-1',
      refresh: vi.fn(),
    });
    const bindSpy = vi.spyOn(workflowService, 'bindWorkflowToCourse').mockResolvedValue({
      id: 'wf-1',
      moodle_course_id: 48,
      status: 'RUNNING',
      stage: 'instructor_review',
    });

    await renderPage();
    await waitFor(() => container.textContent.includes('Eksekusi Struktur Course'), 'Ready button');

    const startBtn = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Eksekusi Struktur Course')
    );
    await act(async () => {
      startBtn.click();
    });

    const confirmBtn = [...container.querySelectorAll('dialog button')].find((b) =>
      b.textContent.includes('Ya, Mulai Eksekusi')
    );
    await act(async () => {
      confirmBtn.click();
    });

    expect(bindSpy).toHaveBeenCalledWith('wf-1', 48, expect.objectContaining({ rpsId: 'rps-1', throwOnError: true }));
    expect(executionService.startExecution).toHaveBeenCalledWith('wf-1', 'STRUCTURE');
  });
});
