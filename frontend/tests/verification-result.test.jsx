import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CourseVerificationPage from '../src/pages/dosen/ai/CourseVerificationPage';
import { api } from '../src/services/apiClient';
import * as executionService from '../src/services/executionService';
import * as verificationService from '../src/services/verificationService';
import * as monitoringSocket from '../src/services/monitoringSocket';
import { DIFF_FILTER, groupVerificationDiffsByWeek, isVerificationPassed } from '../src/utils/verificationResult';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockUseCourse = vi.fn();
vi.mock('../src/hooks/useCourse', () => ({
  useCourse: () => mockUseCourse(),
}));

const fullExecutionSuccess = {
  execution_id: 'exec-full-1',
  workflow_id: 'wf-1',
  scope: 'FULL',
  status: 'SUCCESS',
};

const verificationPass = {
  verification_id: 'ver-pass-1',
  workflow_id: 'wf-1',
  execution_id: 'exec-full-1',
  status: 'PASS',
  matches: true,
  summary: {
    expected_sections: 16,
    actual_sections: 16,
    expected_activities: 4,
    found_activities: 4,
  },
  discrepancies: [],
  repaired: [],
  repair_count: 0,
  repair_rounds: 0,
  error_message: null,
  verified_at: '2026-11-11T10:15:00Z',
};

const verificationPartial = {
  verification_id: 'ver-partial-1',
  workflow_id: 'wf-1',
  execution_id: 'exec-full-1',
  status: 'PARTIAL',
  matches: false,
  summary: {
    expected_sections: 16,
    actual_sections: 16,
    expected_activities: 4,
    found_activities: 4,
  },
  discrepancies: [
    {
      type: 'UNEXPECTED',
      label: 'tidak terduga',
      target: 'ACTIVITY',
      week_number: 2,
      message: "Module forum 'Diskusi Minggu 2' tidak berasal dari eksekusi.",
      expected: {},
      actual: { title: 'Diskusi Minggu 2', modname: 'forum', section: 2 },
      operation_id: null,
      moodle_object_id: 340,
      repairable: false,
    },
  ],
  repaired: [
    {
      type: 'MISSING',
      label: 'hilang',
      target: 'LEARNING_MATERIAL',
      week_number: 1,
      message: 'LEARNING_MATERIAL minggu 1 tidak ada di course (kemungkinan dihapus dari Moodle).',
      expected: { title: 'Konsep Basis Data Relasional', modname: 'page' },
      actual: {},
      operation_id: 'op-mat-1',
      moodle_object_id: 311,
      repairable: true,
    },
  ],
  repair_count: 1,
  repair_rounds: 1,
  error_message: null,
  verified_at: '2026-11-11T10:10:00Z',
};

const verificationFail = {
  verification_id: 'ver-fail-1',
  workflow_id: 'wf-1',
  execution_id: 'exec-full-1',
  status: 'FAIL',
  matches: false,
  summary: {
    expected_sections: 16,
    actual_sections: 15,
    expected_activities: 4,
    found_activities: 2,
  },
  discrepancies: [
    {
      type: 'TITLE_MISMATCH',
      label: 'judul berbeda',
      target: 'QUIZ',
      week_number: 3,
      message: 'Judul QUIZ minggu 3 berbeda.',
      expected: { title: 'Kuis Normalisasi' },
      actual: { title: 'Kuis Lama' },
      operation_id: 'op-quiz-3',
      moodle_object_id: 350,
      repairable: true,
    },
    {
      type: 'WRONG_SECTION',
      label: 'salah section',
      target: 'ASSIGNMENT',
      week_number: 4,
      message: 'ASSIGNMENT minggu 4 berada di section 5.',
      expected: { section: 4 },
      actual: { section: 5 },
      operation_id: 'op-asg-4',
      moodle_object_id: 360,
      repairable: true,
    },
  ],
  repaired: [],
  repair_count: 2,
  repair_rounds: 2,
  error_message: null,
  verified_at: '2026-11-11T10:05:00Z',
};

const verificationUnknown = {
  verification_id: 'ver-unknown-1',
  workflow_id: 'wf-1',
  execution_id: 'exec-full-1',
  status: 'UNKNOWN',
  matches: false,
  summary: null,
  discrepancies: [],
  repaired: [],
  repair_count: 0,
  repair_rounds: 0,
  error_message: 'Server Moodle gagal dihubungi saat membaca isi course.',
  verified_at: '2026-11-11T10:00:00Z',
};

describe('verificationService & helper FE-18.2', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('memanggil endpoint verifikasi dan memetakan error prasyarat 409', async () => {
    const getSpy = vi.spyOn(api, 'get')
      .mockResolvedValueOnce({ items: [verificationPass] })
      .mockResolvedValueOnce(verificationPartial);
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue(verificationPass);

    await expect(verificationService.listWorkflowVerifications('wf-1')).resolves.toEqual([verificationPass]);
    await expect(verificationService.getWorkflowVerification('wf-1', 'ver-partial-1')).resolves.toEqual(verificationPartial);
    await expect(verificationService.startWorkflowVerification('wf-1')).resolves.toEqual(verificationPass);
    await verificationService.startWorkflowVerification('wf-1', 'exec-full-1');

    expect(getSpy).toHaveBeenNthCalledWith(1, '/workflows/wf-1/verifications');
    expect(getSpy).toHaveBeenNthCalledWith(2, '/workflows/wf-1/verifications/ver-partial-1');
    expect(postSpy).toHaveBeenNthCalledWith(1, '/workflows/wf-1/verifications', {});
    expect(postSpy).toHaveBeenNthCalledWith(2, '/workflows/wf-1/verifications', { execution_id: 'exec-full-1' });

    expect(verificationService.formatVerificationPreconditionError({
      details: [{ field: 'reason', message: 'NO_EXECUTION_TO_VERIFY' }],
    })).toContain('eksekusi Moodle cakupan FULL');
    expect(verificationService.formatVerificationPreconditionError({
      details: [{ field: 'reason', message: 'EXECUTION_IN_PROGRESS' }],
    })).toContain('masih berjalan');
  });

  it('mengelompokkan perbedaan tersisa & perbaikan otomatis per minggu sesuai filter', () => {
    const allGroups = groupVerificationDiffsByWeek(verificationPartial, DIFF_FILTER.ALL);
    expect(allGroups.map((g) => g.weekNumber)).toEqual([1, 2]);
    expect(allGroups[0].items[0].repairMeta.label).toBe('Diperbaiki otomatis');
    expect(allGroups[1].items[0].repairMeta.label).toBe('Tambahan manual (dipertahankan)');

    const repairedOnly = groupVerificationDiffsByWeek(verificationPartial, DIFF_FILTER.REPAIRED);
    expect(repairedOnly).toHaveLength(1);
    expect(repairedOnly[0].weekNumber).toBe(1);

    expect(isVerificationPassed(verificationPass)).toBe(true);
    expect(isVerificationPassed(verificationPartial)).toBe(false);
  });
});

describe('FE-18.2 Halaman Hasil Verifikasi Moodle', () => {
  let container;
  let root;
  let refreshSpy;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    refreshSpy = vi.fn();

    mockUseCourse.mockReturnValue({
      course: { id: 'course-1', name: 'Basis Data' },
      moodleCourse: { id: 2, fullname: 'Basis Data' },
      workflow: { id: 'wf-1', moodle_course_id: 2, status: 'RUNNING', stage: 'instructor_review' },
      workflowId: 'wf-1',
      workflowLoading: false,
      refresh: refreshSpy,
    });

    vi.spyOn(monitoringSocket, 'subscribeWorkflowEvents').mockImplementation(() => () => {});
  });

  afterEach(async () => {
    await act(async () => root?.unmount());
    root = null;
    container.remove();
    vi.restoreAllMocks();
  });

  async function renderPage() {
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={['/course/2/ai/verification']}>
          <Routes>
            <Route path="/course/:id/ai/verification" element={<CourseVerificationPage />} />
          </Routes>
        </MemoryRouter>,
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

  it('menampilkan empty state prasyarat saat belum ada eksekusi FULL yang selesai', async () => {
    vi.spyOn(verificationService, 'listWorkflowVerifications').mockResolvedValue([]);
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([
      { execution_id: 'exec-struct-1', scope: 'STRUCTURE', status: 'SUCCESS' },
    ]);

    await renderPage();
    await waitFor(() => container.textContent.includes('Belum ada eksekusi FULL'), 'Empty precondition');

    const publishLink = [...container.querySelectorAll('a')].find((a) =>
      a.getAttribute('href')?.endsWith('/publish'),
    );
    expect(publishLink).toBeTruthy();
  });

  it('menampilkan panduan khusus saat eksekusi FULL sebelumnya berstatus FAILED dengan Gagal: 0 (read-back mismatch)', async () => {
    vi.spyOn(verificationService, 'listWorkflowVerifications').mockResolvedValue([]);
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([
      {
        execution_id: 'exec-full-rb-fail',
        workflow_id: 'wf-1',
        scope: 'FULL',
        status: 'FAILED',
        summary: { total: 80, success: 61, failed: 0, skipped: 19 },
        error_message: 'Hasil read-back tidak sesuai course plan.',
      },
    ]);

    await renderPage();
    await waitFor(
      () => container.textContent.includes('Eksekusi FULL mencatat ketidaksesuaian struktur'),
      'Read-back mismatch guidance on verification page',
    );
    expect(container.textContent).toContain('mengirim 61 operasi tanpa kegagalan operasi');
    expect(container.textContent).toContain('Diharapkan vs Aktual di Moodle');
  });

  it('menjalankan verifikasi awal via POST dan menampilkan hasil PASS serta penanda COMPLETED', async () => {
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([fullExecutionSuccess]);
    const listVerifSpy = vi.spyOn(verificationService, 'listWorkflowVerifications')
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([verificationPass]);
    const startSpy = vi.spyOn(verificationService, 'startWorkflowVerification')
      .mockResolvedValue(verificationPass);

    await renderPage();
    await waitFor(() => container.textContent.includes('Jalankan Verifikasi'), 'Ready button');

    const startBtn = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Jalankan Verifikasi'),
    );
    await act(async () => {
      startBtn.click();
    });

    expect(startSpy).toHaveBeenCalledWith('wf-1');
    await waitFor(() => container.textContent.includes('Course sesuai rencana (COMPLETED)'), 'PASS banner');

    expect(container.textContent).toContain('Sesuai');
    expect(container.textContent).toContain('COMPLETED');
    expect(container.textContent).toContain('16 / 16');
    expect(container.textContent).toContain('4 / 4');
    expect(container.textContent).toContain('ver-pass-1');
    expect(container.textContent).toContain('Tidak ditemukan perbedaan');
    expect(listVerifSpy).toHaveBeenCalledTimes(2);
    expect(refreshSpy).toHaveBeenCalled();

    const courseLink = [...container.querySelectorAll('a')].find((a) =>
      a.getAttribute('href') === '/course/2',
    );
    expect(courseLink).toBeTruthy();
  });

  it('menampilkan perbedaan per minggu (PARTIAL + repaired), filter, dan status perbaikan', async () => {
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([fullExecutionSuccess]);
    vi.spyOn(verificationService, 'listWorkflowVerifications').mockResolvedValue([verificationPartial]);

    await renderPage();
    await waitFor(() => container.textContent.includes('ver-partial-1'), 'Partial verification');

    expect(container.textContent).toContain('Sesuai dengan Catatan');
    expect(container.textContent).toContain('Minggu 1 (1)');
    expect(container.textContent).toContain('Minggu 2 (1)');
    expect(container.textContent).toContain('Konsep Basis Data Relasional');
    expect(container.textContent).toContain('Diperbaiki otomatis');
    expect(container.textContent).toContain('Diskusi Minggu 2');
    expect(container.textContent).toContain('Tambahan di Moodle');
    expect(container.textContent).toContain('Tambahan manual (dipertahankan)');

    // Saring hanya perbedaan yang masih tersisa
    const remainingTab = [...container.querySelectorAll('button[role="tab"]')].find((b) =>
      b.textContent.includes('Masih berbeda (1)'),
    );
    await act(async () => {
      remainingTab.click();
    });
    expect(container.textContent).not.toContain('Konsep Basis Data Relasional');
    expect(container.textContent).toContain('Diskusi Minggu 2');
  });

  it('menampilkan perbedaan FAIL (TITLE_MISMATCH/WRONG_SECTION), UNKNOWN, dan Verifikasi Ulang', async () => {
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([fullExecutionSuccess]);
    vi.spyOn(verificationService, 'listWorkflowVerifications')
      .mockResolvedValueOnce([verificationFail])
      .mockResolvedValueOnce([verificationPass, verificationFail]);
    const startSpy = vi.spyOn(verificationService, 'startWorkflowVerification')
      .mockResolvedValue(verificationPass);

    await renderPage();
    await waitFor(() => container.textContent.includes('ver-fail-1'), 'Fail verification');

    expect(container.textContent).toContain('Tidak Sesuai');
    expect(container.textContent).toContain('Kuis Normalisasi');
    expect(container.textContent).toContain('Judul / nama berbeda');
    expect(container.textContent).toContain('Salah section');
    expect(container.textContent).toContain('Belum terperbaiki');

    const rerunBtn = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Verifikasi Ulang'),
    );
    await act(async () => {
      rerunBtn.click();
    });

    expect(startSpy).toHaveBeenCalledWith('wf-1');
    await waitFor(() => container.textContent.includes('Course sesuai rencana (COMPLETED)'), 'Updated PASS');
    expect(container.textContent).toContain('Riwayat Verifikasi (2)');
  });

  it('menampilkan error UNKNOWN dari Moodle & penolakan prasyarat 409 saat Verifikasi Ulang gagal', async () => {
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([fullExecutionSuccess]);
    vi.spyOn(verificationService, 'listWorkflowVerifications').mockResolvedValue([verificationUnknown]);
    vi.spyOn(verificationService, 'startWorkflowVerification').mockRejectedValue({
      details: [{ field: 'reason', message: 'EXECUTION_IN_PROGRESS' }],
    });

    await renderPage();
    await waitFor(() => container.textContent.includes('ver-unknown-1'), 'Unknown verification');
    expect(container.textContent).toContain('Server Moodle gagal dihubungi saat membaca isi course.');

    const rerunBtn = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Verifikasi Ulang'),
    );
    await act(async () => {
      rerunBtn.click();
    });

    await waitFor(() => container.textContent.includes('Eksekusi ke Moodle masih berjalan.'), '409 alert');
  });

  it('menampilkan riwayat verifikasi dan meninjau detail hasil lama via GET .../verifications/{id}', async () => {
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([fullExecutionSuccess]);
    vi.spyOn(verificationService, 'listWorkflowVerifications').mockResolvedValue([
      verificationPass,
      verificationPartial,
    ]);
    const detailSpy = vi.spyOn(verificationService, 'getWorkflowVerification')
      .mockResolvedValue(verificationPartial);

    await renderPage();
    await waitFor(() => container.textContent.includes('Riwayat Verifikasi (2)'), 'History loaded');

    const reviewBtn = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Tinjau Detail'),
    );
    await act(async () => {
      reviewBtn.click();
    });

    expect(detailSpy).toHaveBeenCalledWith('wf-1', 'ver-partial-1');
    await waitFor(() => container.textContent.includes('Menampilkan riwayat verifikasi terdahulu'), 'Older view');
    expect(container.textContent).toContain('Diskusi Minggu 2');

    const backBtn = [...container.querySelectorAll('button')].find((b) =>
      b.textContent.includes('Kembali ke hasil terbaru'),
    );
    await act(async () => {
      backBtn.click();
    });

    await waitFor(() => container.textContent.includes('Course sesuai rencana (COMPLETED)'), 'Back to latest');
  });
});
