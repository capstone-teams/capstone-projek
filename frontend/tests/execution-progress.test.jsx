import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CoursePublishPage from '../src/pages/dosen/ai/CoursePublishPage';
import * as coursePlanService from '../src/services/coursePlanService';
import * as moodleIntegrationService from '../src/services/moodleIntegrationService';
import * as executionService from '../src/services/executionService';
import * as monitoringSocket from '../src/services/monitoringSocket';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockUseCourse = vi.fn();
vi.mock('../src/hooks/useCourse', () => ({
  useCourse: () => mockUseCourse(),
}));

describe('FE-13.2 Moodle Structure Execution Progress, Operations Detail & Read-Back', () => {
  let container;
  let root;
  let wsCallback;

  const mockPlan = {
    id: 'plan-1',
    version: 1,
    status: 'APPROVED',
    weeks: Array.from({ length: 16 }, (_, i) => ({
      week_number: i + 1,
      title: `Topik Perkuliahan ${i + 1}`,
    })),
  };

  const mockOperations = Array.from({ length: 16 }, (_, i) => ({
    operation_id: `op-${i + 1}`,
    operation_type: 'SECTION',
    status: 'SUCCESS',
    idempotency_key: `wf-1:week:${i + 1}:SECTION`,
    week_number: i + 1,
    moodle_object_id: String(200 + i + 1),
    error_message: null,
    retry_count: 0,
  }));

  const mockRunningExecution = {
    execution_id: 'exec-run-1',
    workflow_id: 'wf-1',
    course_plan_id: 'plan-1',
    scope: 'STRUCTURE',
    status: 'RUNNING',
    moodle_course_id: 2,
    summary: { total: 16, success: 8, failed: 0, skipped: 0 },
    error_message: null,
    created_at: '2026-11-09T08:00:00Z',
    started_at: '2026-11-09T08:00:05Z',
    completed_at: null,
    operations: mockOperations.map((op, idx) => ({
      ...op,
      status: idx < 8 ? 'SUCCESS' : idx === 8 ? 'RUNNING' : 'PENDING',
      moodle_object_id: idx < 8 ? op.moodle_object_id : null,
    })),
    readback: null,
  };

  const mockSuccessExecution = {
    execution_id: 'exec-success-1',
    workflow_id: 'wf-1',
    course_plan_id: 'plan-1',
    scope: 'STRUCTURE',
    status: 'SUCCESS',
    moodle_course_id: 2,
    summary: { total: 16, success: 16, failed: 0, skipped: 0 },
    error_message: null,
    created_at: '2026-11-09T08:00:00Z',
    started_at: '2026-11-09T08:00:05Z',
    completed_at: '2026-11-09T08:00:30Z',
    operations: mockOperations,
    readback: {
      checked: true,
      matches: true,
      expected_sections: 16,
      actual_sections: 16,
      ordered: true,
      missing_weeks: [],
      mismatched_weeks: [],
    },
  };

  const mockFailedExecution = {
    execution_id: 'exec-fail-1',
    workflow_id: 'wf-1',
    course_plan_id: 'plan-1',
    scope: 'STRUCTURE',
    status: 'FAILED',
    moodle_course_id: 2,
    summary: { total: 16, success: 14, failed: 2, skipped: 0 },
    error_message: '2 operasi gagal diterapkan ke Moodle.',
    created_at: '2026-11-09T08:00:00Z',
    started_at: '2026-11-09T08:00:05Z',
    completed_at: '2026-11-09T08:00:25Z',
    operations: mockOperations.map((op, idx) => ({
      ...op,
      status: idx === 3 || idx === 7 ? 'FAILED' : 'SUCCESS',
      moodle_object_id: idx === 3 || idx === 7 ? null : op.moodle_object_id,
      error_message: idx === 3 ? 'Moodle menolak data section 4.' : idx === 7 ? 'Koneksi timeout saat membuat section 8.' : null,
      retry_count: idx === 3 ? 1 : 0,
    })),
    readback: {
      checked: true,
      matches: false,
      expected_sections: 16,
      actual_sections: 14,
      ordered: true,
      missing_weeks: [4, 8],
      mismatched_weeks: [],
    },
  };

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

    vi.spyOn(coursePlanService, 'getWorkflowPlan').mockResolvedValue(mockPlan);
    vi.spyOn(moodleIntegrationService, 'getMoodleStatus').mockResolvedValue({
      status: 'CONNECTED',
      connected: true,
      site_name: 'Moodle Dev ITK',
      release: '4.5+ (Build: 20261001)',
    });

    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([mockRunningExecution]);
    vi.spyOn(executionService, 'getExecution').mockResolvedValue(mockRunningExecution);
    vi.spyOn(executionService, 'retryExecution').mockResolvedValue({
      ...mockFailedExecution,
      status: 'PENDING',
    });

    // Mock subscribeWorkflowEvents untuk pengujian WebSocket
    vi.spyOn(monitoringSocket, 'subscribeWorkflowEvents').mockImplementation((id, onEvent) => {
      wsCallback = onEvent;
      return () => {};
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

  it('menampilkan progress bar, status RUNNING, dan 4 metrik saat eksekusi sedang berjalan', async () => {
    await renderPage();
    await waitFor(() => container.textContent.includes('Status Eksekusi Struktur Moodle'), 'Progress card');

    // Badge status RUNNING
    expect(container.textContent).toContain('RUNNING');
    expect(container.textContent).toContain('exec-run-1');

    // Progress bar (8/16 selesai -> 50%)
    expect(container.textContent).toContain('8/16 (50%)');

    // 4 kotak metrik
    expect(container.textContent).toContain('Total Operasi');
    expect(container.textContent).toContain('Berhasil');
    expect(container.textContent).toContain('Gagal');
    expect(container.textContent).toContain('Dilewati');
  });

  it('memperbarui status operasi mingguan secara reaktif saat menerima event WebSocket WORKFLOW_MOODLE_OPERATION', async () => {
    await renderPage();
    await waitFor(() => container.textContent.includes('Status Eksekusi Struktur Moodle'), 'Progress card');

    // Ubah mock getExecution agar mengembalikan kemajuan 9/16
    const updatedExecution = {
      ...mockRunningExecution,
      summary: { total: 16, success: 9, failed: 0, skipped: 0 },
      operations: mockRunningExecution.operations.map((op, idx) =>
        idx === 8 ? { ...op, status: 'SUCCESS', moodle_object_id: '209' } : op
      ),
    };
    vi.spyOn(executionService, 'getExecution').mockResolvedValue(updatedExecution);

    // Simulasikan event WebSocket operasi Moodle minggu ke-9 selesai
    await act(async () => {
      wsCallback?.({
        event: 'WORKFLOW_MOODLE_OPERATION',
        workflow_id: 'wf-1',
        message: 'Minggu 9 berhasil diterapkan ke Moodle.',
        metadata: {
          execution_id: 'exec-run-1',
          week_number: 9,
          status: 'SUCCESS',
          moodle_object_id: '209',
        },
      });
    });

    // UI harus memperbarui data ke 9/16 secara reaktif
    await waitFor(() => container.textContent.includes('9/16 (56%)'), 'Updated progress bar');
    expect(container.textContent).toContain('Section #209');
  });

  it('menampilkan seluruh 16 section mingguan lengkap dengan moodle_object_id saat status SUCCESS', async () => {
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([mockSuccessExecution]);
    vi.spyOn(executionService, 'getExecution').mockResolvedValue(mockSuccessExecution);

    await renderPage();
    await waitFor(() => container.textContent.includes('16/16 (100%)'), 'Success progress bar');

    expect(container.textContent).toContain('SUCCESS');
    expect(container.textContent).toContain('Struktur 16 section mingguan telah berhasil dibuat');

    // Periksa bahwa section dan judul dari course plan ter-render
    expect(container.textContent).toContain('Minggu 1 - Topik Perkuliahan 1');
    expect(container.textContent).toContain('Minggu 16 - Topik Perkuliahan 16');
    expect(container.textContent).toContain('Section #201');
    expect(container.textContent).toContain('Section #216');
  });

  it('menampilkan hasil verifikasi read-back struktur Moodle yang cocok (matches: true)', async () => {
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([mockSuccessExecution]);
    vi.spyOn(executionService, 'getExecution').mockResolvedValue(mockSuccessExecution);

    await renderPage();
    await waitFor(() => container.textContent.includes('Verifikasi Read-Back Struktur Moodle'), 'Readback panel');

    expect(container.textContent).toContain('Struktur Sesuai');
    expect(container.textContent).toContain('Seluruh 16 section mingguan pada kursus Moodle telah diverifikasi');
    expect(container.textContent).toContain('100% Sesuai');
    expect(container.textContent).toContain('Terurut (1–16)');
  });

  it('menampilkan peringatan ketidakcocokan read-back dan pesan error pada section yang gagal (matches: false)', async () => {
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([mockFailedExecution]);
    vi.spyOn(executionService, 'getExecution').mockResolvedValue(mockFailedExecution);

    await renderPage();
    await waitFor(() => container.textContent.includes('Ada Ketidaksesuaian'), 'Readback mismatch');

    // Panel readback menunjukkan ketidakcocokan
    expect(container.textContent).toContain('Struktur Moodle Belum Sesuai Sepenuhnya');
    expect(container.textContent).toContain('Minggu yang belum ditemukan di Moodle: Minggu 4, 8');

    // Tabel operasi menunjukkan pesan error spesifik
    expect(container.textContent).toContain('Moodle menolak data section 4.');
    expect(container.textContent).toContain('Koneksi timeout saat membuat section 8.');
    expect(container.textContent).toContain('(Dicoba ulang: 1x)');
  });

  it('menampilkan tombol Ulangi Operasi Gagal dan berhasil memanggil retryExecution saat diklik', async () => {
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([mockFailedExecution]);
    vi.spyOn(executionService, 'getExecution').mockResolvedValue(mockFailedExecution);

    await renderPage();
    await waitFor(() => container.textContent.includes('Ulangi Operasi Gagal'), 'Retry button');

    const retryBtn = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Ulangi Operasi Gagal')
    );
    expect(retryBtn).toBeTruthy();

    await act(async () => {
      retryBtn.click();
    });

    // Memverifikasi retryExecution dipanggil dengan workflowId dan executionId yang tepat
    expect(executionService.retryExecution).toHaveBeenCalledWith('wf-1', 'exec-fail-1');
  });

  it('menampilkan riwayat eksekusi dan dapat beralih meninjau eksekusi lama', async () => {
    const pastExecutions = [mockRunningExecution, mockSuccessExecution];
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue(pastExecutions);
    vi.spyOn(executionService, 'getExecution').mockImplementation((wfId, execId) => {
      if (execId === 'exec-success-1') return Promise.resolve(mockSuccessExecution);
      return Promise.resolve(mockRunningExecution);
    });

    await renderPage();
    await waitFor(() => container.textContent.includes('Riwayat Eksekusi Struktur Moodle'), 'History card');

    expect(container.textContent).toContain('exec-run-1');
    expect(container.textContent).toContain('exec-success-1');
    expect(container.textContent).toContain('● Sedang Ditinjau');

    // Klik tombol Tinjau Detail pada eksekusi lama (exec-success-1)
    const reviewBtn = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Tinjau Detail')
    );
    expect(reviewBtn).toBeTruthy();

    await act(async () => {
      reviewBtn.click();
    });

    // Detail beralih ke exec-success-1
    await waitFor(() => container.textContent.includes('16/16 (100%)'), 'Switched execution detail');
    expect(executionService.getExecution).toHaveBeenCalledWith('wf-1', 'exec-success-1');
  });
});
