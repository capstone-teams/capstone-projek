import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../src/context/AuthProvider';
import { AppStateProvider } from '../src/context/AppStateProvider';
import App from '../src/App';
import { login as backendLogin } from '../src/services/authService';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';
import * as rpsService from '../src/services/rpsService';
import * as workflowService from '../src/services/workflowService';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe('FE-11.1 Dashboard Dosen', () => {
  let container;
  let root;

  beforeAll(() => {
    configureMock({ latencyMs: 0, stepMs: 5 });
  });

  beforeEach(() => {
    resetMockDb();
    localStorage.clear();
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(() => {
    act(() => root?.unmount());
    root = null;
    container.remove();
    vi.restoreAllMocks();
  });

  async function renderDashboard() {
    await backendLogin('dosen', 'dosen123');
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={['/my']}>
          <AuthProvider>
            <AppStateProvider>
              <App />
            </AppStateProvider>
          </AuthProvider>
        </MemoryRouter>,
      );
    });
  }

  async function waitFor(check, label, timeout = 4000) {
    const start = Date.now();
    while (!check()) {
      if (Date.now() - start > timeout) {
        throw new Error(`Timeout: ${label}. Isi: ${container.textContent.slice(0, 400)}`);
      }
      await act(() => new Promise((r) => setTimeout(r, 20)));
    }
  }

  it('menampilkan salam dan card ringkasan terpadu', async () => {
    await renderDashboard();
    await waitFor(() => container.textContent.includes('Halo,'), 'Salam dosen');

    expect(container.textContent).toContain('Dasbor ringkasan aktivitas pengajaran');
    expect(container.textContent).toContain('Timeline');
    expect(container.textContent).toContain('Kursus yang Anda ajar');
    expect(container.textContent).toContain('RPS & Dokumen Akademik');

    // Tombol unggah cepat di header kartu RPS
    const buttons = [...container.querySelectorAll('button')];
    const uploadBtn = buttons.find((b) => b.textContent.includes('Unggah'));
    expect(uploadBtn).toBeTruthy();

    // Tautan monitoring teknis di header card RPS
    const links = [...container.querySelectorAll('a')];
    const monitorLink = links.find((a) => a.textContent.includes('Monitoring ↗'));
    expect(monitorLink).toBeTruthy();
    expect(monitorLink.getAttribute('href')).toMatch(/\/course\/[^/]+\/ai\/workflows/);
  });

  it('menampilkan daftar RPS dosen dengan nama file dan badge status', async () => {
    vi.spyOn(rpsService, 'listRps').mockResolvedValue({
      items: [
        {
          id: 'rps-demo-1',
          filename: 'RPS-Kecerdasan-Buatan.pdf',
          status: 'ANALYZED',
          created_at: '2026-11-05T10:00:00Z',
          workflow_id: 'wf-demo-1',
        },
      ],
    });

    await renderDashboard();
    await waitFor(() => container.textContent.includes('RPS-Kecerdasan-Buatan.pdf'), 'Daftar RPS');

    expect(container.textContent).toContain('Selesai dianalisis');
    const links = [...container.querySelectorAll('a')];
    const analysisLink = links.find((a) => a.textContent.includes('Hasil Analisis'));
    expect(analysisLink).toBeTruthy();
    expect(analysisLink.getAttribute('href')).toContain('rps=rps-demo-1');
  });

  it('menampilkan empty state jika belum ada RPS yang diunggah', async () => {
    vi.spyOn(rpsService, 'listRps').mockResolvedValue({ items: [] });

    await renderDashboard();
    await waitFor(() => container.textContent.includes('Belum ada dokumen RPS.'), 'Empty state RPS');

    const emptyAction = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Unggah RPS Sekarang'),
    );
    expect(emptyAction).toBeTruthy();
  });

  it('menampilkan aksi review langsung pada item dokumen jika membutuhkan persetujuan', async () => {
    vi.spyOn(rpsService, 'listRps').mockResolvedValue({
      items: [
        {
          id: 'rps-rev-1',
          filename: 'RPS-Basis-Data.pdf',
          status: 'ANALYZED',
          created_at: '2026-11-06T10:00:00Z',
          workflow_id: 'wf-review-1',
        },
      ],
    });
    vi.spyOn(workflowService, 'listWorkflows').mockResolvedValue([
      {
        id: 'wf-review-1',
        status: 'RUNNING',
        stage: 'instructor_review',
        moodle_course_id: 2,
        updated_at: '2026-11-07T09:00:00Z',
      },
    ]);

    await renderDashboard();
    await waitFor(
      () => container.textContent.includes('RPS-Basis-Data.pdf'),
      'Item dokumen review',
    );

    // Badge status review & tautan aksi kontekstual yang bersih
    expect(container.textContent).toContain('Menunggu review Anda');
    const links = [...container.querySelectorAll('a')];
    const reviewBtn = links.find((a) => a.textContent.includes('Review Sekarang →'));
    expect(reviewBtn).toBeTruthy();
    expect(reviewBtn.getAttribute('href')).toBe('/course/2/ai/review');
  });

  it('menampilkan aksi lihat masalah jika pemrosesan dokumen mengalami kegagalan', async () => {
    vi.spyOn(rpsService, 'listRps').mockResolvedValue({
      items: [
        {
          id: 'rps-fail-1',
          filename: 'RPS-Jaringan-Komputer.pdf',
          status: 'FAILED',
          created_at: '2026-11-07T10:00:00Z',
          workflow_id: 'wf-fail-1',
        },
      ],
    });
    vi.spyOn(workflowService, 'listWorkflows').mockResolvedValue([
      {
        id: 'wf-fail-1',
        status: 'FAILED',
        stage: 'moodle_execution',
        moodle_course_id: 2,
        updated_at: '2026-11-07T10:00:00Z',
      },
    ]);

    await renderDashboard();
    await waitFor(
      () => container.textContent.includes('RPS-Jaringan-Komputer.pdf'),
      'Item dokumen gagal',
    );

    const links = [...container.querySelectorAll('a')];
    const problemBtn = links.find((a) => a.textContent.includes('Lihat Masalah'));
    expect(problemBtn).toBeTruthy();
    expect(problemBtn.getAttribute('href')).toContain('workflow=wf-fail-1');

    // Memastikan tidak ada tombol redundan "Pantau" di samping "Lihat Masalah"
    const pantauBtn = links.find((a) => a.textContent.trim() === 'Pantau');
    expect(pantauBtn).toBeFalsy();
  });

  it('dapat membuka dan menutup modal unggah RPS dari tombol pada card dokumen', async () => {
    await renderDashboard();
    await waitFor(() => container.textContent.includes('Halo,'), 'Salam dosen');

    const uploadBtn = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Unggah'),
    );
    expect(uploadBtn).toBeTruthy();

    await act(async () => {
      uploadBtn.click();
    });

    await waitFor(() => container.querySelector('dialog'), 'Modal unggah RPS');
    expect(container.querySelector('dialog').textContent).toContain('Unggah Dokumen RPS');

    // Tutup modal
    const closeBtn = container.querySelector('dialog button[aria-label="Tutup"]')
      || container.querySelector('dialog button');
    expect(closeBtn).toBeTruthy();
    await act(async () => {
      closeBtn.click();
    });

    expect(container.querySelector('dialog')).toBeNull();
  });

  it('hanya menampilkan RPS aktif per kursus dan menyembunyikan RPS lama yang sudah digantikan (Opsi 1)', async () => {
    vi.spyOn(rpsService, 'listRps').mockResolvedValue({
      items: [
        {
          id: 'rps-baru-1',
          filename: 'RPS-Basis-Data-2026-Baru.pdf',
          status: 'ANALYZED',
          created_at: '2026-11-08T12:00:00Z',
          workflow_id: 'wf-baru-1',
        },
        {
          id: 'rps-lama-1',
          filename: 'RPS-Basis-Data-2022-Lama.pdf',
          status: 'FAILED',
          created_at: '2026-11-01T10:00:00Z',
          workflow_id: 'wf-lama-1',
        },
      ],
    });
    vi.spyOn(workflowService, 'listWorkflows').mockResolvedValue([
      {
        id: 'wf-baru-1',
        status: 'RUNNING',
        stage: 'instructor_review',
        moodle_course_id: 2,
        updated_at: '2026-11-08T12:00:00Z',
      },
      {
        id: 'wf-lama-1',
        status: 'FAILED',
        stage: 'rps_analysis',
        moodle_course_id: 2,
        updated_at: '2026-11-01T10:00:00Z',
      },
    ]);

    await renderDashboard();
    await waitFor(
      () => container.textContent.includes('RPS-Basis-Data-2026-Baru.pdf'),
      'RPS baru tampil',
    );

    // RPS aktif terbaru ditampilkan
    expect(container.textContent).toContain('RPS-Basis-Data-2026-Baru.pdf');
    // RPS lama yang sudah digantikan untuk kursus yang sama disembunyikan
    expect(container.textContent).not.toContain('RPS-Basis-Data-2022-Lama.pdf');
  });

  it('tetap menampilkan RPS aktif yang baru dianalisis meskipun workflow summary backend tidak memuat moodle_course_id', async () => {
    sessionStorage.clear();
    vi.spyOn(rpsService, 'listRps').mockResolvedValue({
      items: [
        {
          id: 'rps-sbd-1',
          filename: 'RPS SBD Genap 2223.pdf',
          status: 'ANALYZED',
          created_at: '2026-11-08T13:55:00Z',
          workflow_id: 'wf-sbd-1',
        },
        {
          id: 'rps-fail-old-1',
          filename: 'RPS Fisika Dasar 1 2020-2025.pdf',
          status: 'FAILED',
          created_at: '2026-11-04T23:50:00Z',
        },
        {
          id: 'rps-fail-old-2',
          filename: 'Contoh RPS.pdf',
          status: 'FAILED',
          created_at: '2026-11-02T17:23:00Z',
        },
      ],
    });
    // Sesuai kontrak backend GET /workflows (WorkflowSummary), moodle_course_id tidak dikirim di ringkasan
    vi.spyOn(workflowService, 'listWorkflows').mockResolvedValue([
      {
        id: 'wf-sbd-1',
        status: 'RUNNING',
        stage: 'instructor_review',
        rps_id: 'rps-sbd-1',
        updated_at: '2026-11-08T13:55:00Z',
      },
    ]);

    await renderDashboard();
    await waitFor(
      () => container.textContent.includes('RPS SBD Genap 2223.pdf'),
      'RPS aktif SBD tampil di kartu dasbor',
    );

    // Dokumen aktif SBD harus tampil
    expect(container.textContent).toContain('RPS SBD Genap 2223.pdf');
    // Dokumen lama yang gagal disembunyikan (Opsi 1)
    expect(container.textContent).not.toContain('RPS Fisika Dasar 1 2020-2025.pdf');
    expect(container.textContent).not.toContain('Contoh RPS.pdf');
    // Kartu TIDAK boleh menampilkan pesan kosong 'Belum ada dokumen RPS'
    expect(container.textContent).not.toContain('Belum ada dokumen RPS.');
  });
});
