import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { AuthProvider } from '../src/context/AuthProvider';
import { AppStateProvider } from '../src/context/AppStateProvider';
import AiCourseLayout from '../src/pages/dosen/ai/AiCourseLayout';
import CourseRpsPage from '../src/pages/dosen/ai/CourseRpsPage';
import CourseRpsBar from '../src/components/ai/course/CourseRpsBar';
import { login as backendLogin } from '../src/services/authService';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';
import { api } from '../src/services/apiClient';
import * as workflowService from '../src/services/workflowService';
import * as rpsService from '../src/services/rpsService';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function CourseWrapper({ courseId = 2 }) {
  return (
    <Outlet
      context={{
        course: { id: courseId, shortname: 'IF2230', fullname: 'Basis Data', moodle_course_id: courseId },
        isTeacher: true,
      }}
    />
  );
}

describe('In-Course RPS Overwrite & Background Persistence', () => {
  let container;
  let root;

  beforeAll(() => {
    configureMock({ latencyMs: 0, stepMs: 5 });
  });

  beforeEach(() => {
    resetMockDb();
    workflowService.clearWorkflowCache();
    localStorage.clear();
    sessionStorage.clear();
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(() => {
    act(() => root?.unmount());
    root = null;
    container.remove();
    vi.restoreAllMocks();
  });

  async function renderCourseRps(courseId = 2) {
    await backendLogin('dosen', 'dosen123');
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={[`/course/${courseId}/ai/rps`]}>
          <AuthProvider>
            <AppStateProvider>
              <Routes>
                <Route element={<CourseWrapper courseId={courseId} />}>
                  <Route path="/course/:id/ai" element={<AiCourseLayout />}>
                    <Route path="rps" element={<CourseRpsPage />} />
                  </Route>
                </Route>
              </Routes>
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
        throw new Error(`Timeout: ${label}. Content: ${container.textContent.slice(0, 400)}`);
      }
      await act(() => new Promise((r) => setTimeout(r, 20)));
    }
  }

  it('bindWorkflowToCourse mengikat target kursus baru dan melepaskan workflow lama', async () => {
    const putSpy = vi.spyOn(api, 'put').mockImplementation(async (path, body) => ({
      id: path.split('/')[2],
      moodle_course_id: body.moodle_course_id,
    }));

    vi.spyOn(api, 'get').mockImplementation(async (path) => {
      if (path === '/workflows') {
        return {
          items: [
            { id: 'wf-old', status: 'COMPLETED', rps_id: 'rps-old', updated_at: '2026-11-08T00:00:00Z' },
          ],
        };
      }
      if (path === '/workflows/wf-old') {
        return { id: 'wf-old', moodle_course_id: 2, status: 'COMPLETED', updated_at: '2026-11-08T00:00:00Z' };
      }
      return null;
    });

    await workflowService.bindWorkflowToCourse('wf-new', 2);

    // Harus memanggil PUT untuk wf-new dengan moodle_course_id: 2
    expect(putSpy).toHaveBeenCalledWith('/workflows/wf-new/moodle-target', { moodle_course_id: 2 });
    // Dan memanggil PUT untuk wf-old dengan moodle_course_id: null
    expect(putSpy).toHaveBeenCalledWith('/workflows/wf-old/moodle-target', { moodle_course_id: null });
  });

  it('menampilkan status pemrosesan background dan tidak jatuh ke berkas lama saat workflow sedang berjalan', async () => {
    // Simulasi ada workflow aktif untuk kursus 2 yang sedang memproses RPS baru "RPS MBD 2223.pdf"
    vi.spyOn(workflowService, 'findWorkflowForCourse').mockResolvedValue({
      id: 'wf-active-mbd',
      rps_id: 'rps-mbd-new',
      status: 'RUNNING',
      stage: 'rps_analysis',
      progress: { completed: 1, total: 2 },
      moodle_course_id: 2,
    });

    vi.spyOn(rpsService, 'getRps').mockResolvedValue({
      id: 'rps-mbd-new',
      filename: 'RPS MBD 2223.pdf',
      status: 'ANALYZING',
      workflow_id: 'wf-active-mbd',
      has_source_document: true,
    });

    await renderCourseRps(2);

    await waitFor(() => container.textContent.includes('RPS MBD 2223.pdf'), 'Menampilkan berkas baru');

    // Berkas baru tampil, bukan berkas lama contoh-rps-basis-data.pdf
    expect(container.textContent).toContain('RPS MBD 2223.pdf');
    expect(container.textContent).not.toContain('contoh-rps-basis-data.pdf');

    // Indikator background processing tampil
    expect(container.textContent).toContain('Pemrosesan RPS sedang berlangsung');
    expect(container.textContent).toContain('Proses berjalan di background walau Anda berpindah halaman.');
  });

  it('menampilkan tombol Ganti RPS di header halaman agar dosen dapat mengganti dokumen kapan saja', async () => {
    vi.spyOn(workflowService, 'findWorkflowForCourse').mockResolvedValue({
      id: 'wf-active-mbd',
      rps_id: 'rps-mbd-new',
      status: 'WAITING_FOR_REVIEW',
      stage: 'instructor_review',
      progress: { completed: 2, total: 2 },
      moodle_course_id: 2,
    });

    vi.spyOn(rpsService, 'getRps').mockResolvedValue({
      id: 'rps-mbd-new',
      filename: 'RPS MBD 2223.pdf',
      status: 'ANALYZED',
      workflow_id: 'wf-active-mbd',
      has_source_document: true,
    });

    vi.spyOn(rpsService, 'getRpsAnalysis').mockResolvedValue({
      rps_id: 'rps-mbd-new',
      analyzed_at: '2026-11-09T10:00:00Z',
      data: {
        course: { code: 'IF2230', name: 'Manajemen Basis Data', credits: 3 },
        cpmk: [{ code: 'CPMK-1', description: 'Memahami konsep' }],
        weekly_plan: [{ week: 1, topic: 'Pengantar', sub_cpmk: ['SUB-1'], teaching_methods: ['Ceramah'] }],
      },
    });

    await renderCourseRps(2);

    await waitFor(() => container.textContent.includes('RPS MBD 2223.pdf'), 'Menampilkan berkas RPS selesai');

    const replaceBtn = [...container.querySelectorAll('button')].find((b) => b.textContent.includes('Ganti RPS'));
    expect(replaceBtn).toBeTruthy();

    // Klik tombol Ganti RPS membuka form upload pengganti
    await act(async () => {
      replaceBtn.click();
    });

    expect(container.textContent).toContain('Unggah RPS Pengganti');
    expect(container.textContent).toContain('Mengunggah RPS baru akan menggantikan RPS aktif saat ini');
  });

  it('navigasi ke halaman lain dan kembali saat analisis berjalan tetap mempertahankan RPS baru dan tidak jatuh ke contoh-rps-basis-data.pdf', async () => {
    // 1. Simulasikan user baru saja mengunggah "RPS SBD Genap 2223.pdf" dan tersimpan di activeBinding
    workflowService.saveActiveCourseBinding(2, {
      workflowId: 'wf-sbd-running',
      rpsId: 'rps-sbd-new',
    });

    // Mock API workflows & getRps
    vi.spyOn(api, 'get').mockImplementation(async (path) => {
      if (path === '/workflows/wf-sbd-running') {
        return {
          id: 'wf-sbd-running',
          rps_id: 'rps-sbd-new',
          status: 'RUNNING',
          stage: 'rps_analysis',
          progress_completed: 1,
          progress_total: 2,
          moodle_course_id: 2,
        };
      }
      if (path === '/workflows') {
        return {
          items: [
            { id: 'wf-sbd-running', status: 'RUNNING', rps_id: 'rps-sbd-new' },
            { id: 'wf-old-contoh', status: 'FAILED', rps_id: 'rps-contoh-gagal' },
          ],
        };
      }
      if (path === '/workflows/wf-old-contoh') {
        return { id: 'wf-old-contoh', status: 'FAILED', rps_id: 'rps-contoh-gagal', moodle_course_id: 2 };
      }
      if (path === '/courses/IF2230') {
        return { id: 'IF2230', moodle_course_id: 2, rps_id: 'rps-contoh-gagal', fullname: 'Basis Data (Contoh)' };
      }
      return null;
    });

    vi.spyOn(rpsService, 'getRps').mockImplementation(async (id) => {
      if (id === 'rps-sbd-new') {
        return {
          id: 'rps-sbd-new',
          filename: 'RPS SBD Genap 2223.pdf',
          status: 'ANALYZING',
          workflow_id: 'wf-sbd-running',
          has_source_document: true,
        };
      }
      if (id === 'rps-contoh-gagal') {
        return {
          id: 'rps-contoh-gagal',
          filename: 'contoh-rps-basis-data.pdf',
          status: 'FAILED',
          workflow_id: 'wf-old-contoh',
          processing_error_message: 'Penyimpanan dokumen gagal.',
        };
      }
      return null;
    });

    // Render halaman pertama kali (seolah-olah kembali dari halaman lain/refresh)
    await renderCourseRps(2);

    await waitFor(() => container.textContent.includes('RPS SBD Genap 2223.pdf'), 'Menampilkan RPS baru');

    // Pastikan berkas baru yang tampil dan berstatus sedang diproses
    expect(container.textContent).toContain('RPS SBD Genap 2223.pdf');
    expect(container.textContent).not.toContain('contoh-rps-basis-data.pdf');
    expect(container.textContent).toContain('Pemrosesan RPS sedang berlangsung');

    // 2. Simulasikan user navigasi ke halaman lain (unmount)
    await act(async () => {
      root.unmount();
      root = null;
    });

    // 3. Simulasikan user kembali lagi ke tab RPS (remount)
    await renderCourseRps(2);

    await waitFor(() => container.textContent.includes('RPS SBD Genap 2223.pdf'), 'Kembali menampilkan RPS baru');

    // Tetap menampilkan RPS baru yang sedang berjalan dan TIDAK PERNAH kembali ke contoh-rps-basis-data.pdf
    expect(container.textContent).toContain('RPS SBD Genap 2223.pdf');
    expect(container.textContent).not.toContain('contoh-rps-basis-data.pdf');
    expect(container.textContent).toContain('Pemrosesan RPS sedang berlangsung');
  });

  it('ketika analisis workflow RPS baru selesai, halaman menampilkan hasil analisis RPS baru dan tidak kembali ke contoh-rps-basis-data.pdf', async () => {
    // 1. Simulasikan binding sudah ada untuk RPS baru
    workflowService.saveActiveCourseBinding(2, {
      workflowId: 'wf-sbd-finished',
      rpsId: 'rps-sbd-analyzed',
    });

    vi.spyOn(api, 'get').mockImplementation(async (path) => {
      if (path === '/workflows/wf-sbd-finished') {
        return {
          id: 'wf-sbd-finished',
          rps_id: 'rps-sbd-analyzed',
          status: 'WAITING_FOR_REVIEW',
          stage: 'instructor_review',
          progress_completed: 2,
          progress_total: 2,
          moodle_course_id: 2,
        };
      }
      if (path === '/workflows') {
        return {
          items: [
            { id: 'wf-sbd-finished', status: 'WAITING_FOR_REVIEW', rps_id: 'rps-sbd-analyzed' },
            { id: 'wf-old-contoh', status: 'FAILED', rps_id: 'rps-contoh-gagal' },
          ],
        };
      }
      if (path === '/courses/IF2230') {
        return { id: 'IF2230', moodle_course_id: 2, rps_id: 'rps-contoh-gagal' };
      }
      return null;
    });

    vi.spyOn(rpsService, 'getRps').mockImplementation(async (id) => {
      if (id === 'rps-sbd-analyzed') {
        return {
          id: 'rps-sbd-analyzed',
          filename: 'RPS SBD Genap 2223.pdf',
          status: 'ANALYZED',
          workflow_id: 'wf-sbd-finished',
          has_source_document: true,
        };
      }
      return null;
    });

    vi.spyOn(rpsService, 'getRpsAnalysis').mockResolvedValue({
      rps_id: 'rps-sbd-analyzed',
      analyzed_at: '2026-11-09T15:40:00Z',
      data: {
        course: { code: 'IF2230', name: 'Sistem Basis Data', credits: 3 },
        cpmk: [{ code: 'CPMK-1', description: 'Memahami arsitektur basis data' }],
        weekly_plan: [{ week: 1, topic: 'Pengantar Basis Data', sub_cpmk: ['SUB-1'], teaching_methods: ['Ceramah'] }],
      },
    });

    await renderCourseRps(2);

    await waitFor(() => container.textContent.includes('RPS SBD Genap 2223.pdf'), 'Menampilkan berkas RPS selesai');

    // Halaman harus menampilkan detail analisis baru
    expect(container.textContent).toContain('RPS SBD Genap 2223.pdf');
    expect(container.textContent).not.toContain('contoh-rps-basis-data.pdf');
    expect(container.textContent).toContain('Memahami arsitektur basis data');
    expect(container.textContent).toContain('Lanjut ke Course Planning');
  });

  it('CourseRpsBar pada tab Kursus menampilkan RPS aktif dari binding lokal jika sudah di-overwrite', async () => {
    // Binding lokal sudah mereferensikan berkas baru
    workflowService.saveActiveCourseBinding('IF2230-SAMPLE', {
      workflowId: 'wf-sbd-active',
      rpsId: 'rps-sbd-active',
    }, ['IF2230', '2']);

    vi.spyOn(rpsService, 'getRps').mockImplementation(async (id) => {
      if (id === 'rps-sbd-active') {
        return {
          id: 'rps-sbd-active',
          filename: 'RPS SBD Genap 2223.pdf',
          status: 'ANALYZED',
        };
      }
      if (id === 'rps-old-seed') {
        return {
          id: 'rps-old-seed',
          filename: 'contoh-rps-basis-data.pdf',
          status: 'FAILED',
        };
      }
      return null;
    });

    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter>
          <CourseRpsBar
            course={{
              id: 'IF2230-SAMPLE',
              shortname: 'IF2230-SAMPLE',
              rps_id: 'rps-old-seed',
            }}
          />
        </MemoryRouter>,
      );
    });

    await waitFor(() => container.textContent.includes('RPS SBD Genap 2223.pdf'), 'Menampilkan RPS baru di CourseRpsBar');

    expect(container.textContent).toContain('RPS SBD Genap 2223.pdf');
    expect(container.textContent).not.toContain('contoh-rps-basis-data.pdf');
    expect(container.textContent).toContain('Selesai dianalisis');
    expect(container.textContent).toContain('Hasil analisis');
  });
});
