import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthContext } from '../src/context/authContext';
import { AppStateProvider } from '../src/context/AppStateProvider';
import DosenActivityPage from '../src/pages/dosen/course/ActivityPage';
import MahasiswaActivityPage from '../src/pages/mahasiswa/course/ActivityPage';
import * as contentService from '../src/services/contentService';
import * as executionService from '../src/services/executionService';
import * as monitoringSocket from '../src/services/monitoringSocket';
import * as workflowService from '../src/services/workflowService';
import {
  canRegenerateWorkflowContent,
  findOperationForMoodleCm,
  resolveContentForOperation,
} from '../src/utils/activityRegeneration';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockMoodleCourse = vi.hoisted(() => ({
  course: { id: 48, fullname: 'Pemrograman Web', shortname: 'PW-2223' },
  sections: [
    {
      id: 10,
      section: 1,
      name: 'Minggu 1: Dasar Web',
      modules: [
        {
          id: 311,
          name: 'Minggu 1: Dasar Web',
          modname: 'page',
          content: '<p>Isi materi dasar web.</p>',
          visible: 1,
          uservisible: true,
        },
        {
          id: 84,
          name: 'Announcements',
          modname: 'forum',
          description: '<p>Forum pengumuman manual</p>',
          visible: 1,
          uservisible: true,
        },
      ],
    },
  ],
}));

vi.mock('../src/hooks/useMoodleCourse', () => ({
  useMoodleCourse: () => mockMoodleCourse,
  useCourseBreadcrumb: () => {},
}));

describe('Utilitas activityRegeneration', () => {
  it('mencocokkan cmid Moodle ke operasi eksekusi FULL dan versi konten terbaru', () => {
    const executions = [
      {
        execution_id: 'exec-full-1',
        scope: 'FULL',
        operations: [
          { operation_id: 'op-s1', operation_type: 'SECTION', status: 'SUCCESS', week_number: 1, moodle_object_id: '10' },
          { operation_id: 'op-m1', operation_type: 'LEARNING_MATERIAL', status: 'SUCCESS', week_number: 1, content_id: 'ct-v1', moodle_object_id: '311', title: 'Dasar Web' },
        ],
      },
    ];
    const op = findOperationForMoodleCm(executions, '311');
    expect(op?.content_id).toBe('ct-v1');
    expect(findOperationForMoodleCm(executions, '84')).toBeNull();

    const latest = resolveContentForOperation(
      [{ id: 'ct-v2', week_number: 1, kind: 'LEARNING_MATERIAL', version: 2, status: 'DRAFT' }],
      op,
    );
    expect(latest.id).toBe('ct-v2');
    expect(latest.version).toBe(2);

    expect(canRegenerateWorkflowContent({ status: 'RUNNING', stage: 'instructor_review' }).allowed).toBe(true);
    expect(canRegenerateWorkflowContent({ status: 'FAILED' }).allowed).toBe(true);
    expect(canRegenerateWorkflowContent({ status: 'RUNNING', stage: 'content_generation' }).allowed).toBe(false);
    expect(canRegenerateWorkflowContent({ status: 'COMPLETED' }).allowed).toBe(false);
  });
});

describe('Tombol Regenerasi Konten pada Halaman Activity', () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.spyOn(monitoringSocket, 'subscribeWorkflowEvents').mockImplementation(() => () => {});
  });

  afterEach(async () => {
    await act(async () => root?.unmount());
    root = null;
    container.remove();
    vi.restoreAllMocks();
  });

  async function renderDosenActivity(cmid) {
    root = createRoot(container);
    await act(async () => {
      root.render(
        <AuthContext.Provider value={{ user: { id: 3, role: 'DOSEN' } }}>
          <AppStateProvider>
            <MemoryRouter initialEntries={[`/course/48/mod/${cmid}`]}>
              <Routes>
                <Route path="/course/:courseId/mod/:cmid" element={<DosenActivityPage />} />
              </Routes>
            </MemoryRouter>
          </AppStateProvider>
        </AuthContext.Provider>,
      );
    });
  }

  async function renderMahasiswaActivity(cmid) {
    root = createRoot(container);
    await act(async () => {
      root.render(
        <AuthContext.Provider value={{ user: { id: 7, role: 'MAHASISWA' } }}>
          <AppStateProvider>
            <MemoryRouter initialEntries={[`/course/48/mod/${cmid}`]}>
              <Routes>
                <Route path="/course/:courseId/mod/:cmid" element={<MahasiswaActivityPage />} />
              </Routes>
            </MemoryRouter>
          </AppStateProvider>
        </AuthContext.Provider>,
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

  it('menampilkan tombol Regenerasi konten untuk aktivitas hasil AI dan memanggil POST .../contents/regenerate scope ITEM', async () => {
    const waitingWf = { id: 'wf-1', moodle_course_id: 48, status: 'RUNNING', stage: 'instructor_review' };
    vi.spyOn(workflowService, 'findWorkflowForCourse').mockResolvedValue(waitingWf);
    vi.spyOn(workflowService, 'getWorkflow').mockResolvedValue(waitingWf);
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([
      { execution_id: 'exec-full-1', scope: 'FULL', status: 'SUCCESS' },
    ]);
    vi.spyOn(executionService, 'getExecution').mockResolvedValue({
      execution_id: 'exec-full-1',
      scope: 'FULL',
      operations: [
        {
          operation_id: 'op-m1',
          operation_type: 'LEARNING_MATERIAL',
          status: 'SUCCESS',
          week_number: 1,
          content_id: 'ct-1',
          moodle_object_id: '311',
          title: 'Dasar Web',
        },
      ],
    });
    vi.spyOn(contentService, 'listWorkflowContents')
      .mockResolvedValueOnce([
        { id: 'ct-1', week_number: 1, kind: 'LEARNING_MATERIAL', version: 1, status: 'EXECUTED' },
      ])
      .mockResolvedValue([
        { id: 'ct-2', week_number: 1, kind: 'LEARNING_MATERIAL', version: 2, status: 'DRAFT' },
      ]);
    const regenSpy = vi.spyOn(contentService, 'regenerateWorkflowContents').mockResolvedValue({
      workflow_id: 'wf-1',
      status: 'GENERATING_CONTENT',
      message: 'Regenerasi konten dijadwalkan; pantau status workflow dan event untuk hasilnya.',
    });

    await renderDosenActivity(311);
    await waitFor(() => container.textContent.includes('Regenerasi konten'), 'Regenerate button');
    expect(container.textContent).toContain('Isi materi dasar web.');

    const regenBtn = [...container.querySelectorAll('button')].find((b) => b.textContent.includes('Regenerasi konten'));
    await act(async () => {
      regenBtn.click();
    });

    await waitFor(() => container.textContent.includes('Regenerasi Minggu 1 — Materi pembelajaran'), 'Modal title');

    // Validasi wajib mengisi catatan revisi
    const submitBtn = [...container.querySelectorAll('button')].find((b) => b.textContent.includes('Mulai Regenerasi'));
    await act(async () => {
      submitBtn.click();
    });
    expect(container.textContent).toContain('Catatan revisi wajib diisi.');
    expect(regenSpy).not.toHaveBeenCalled();

    const textarea = container.querySelector('textarea');
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(textarea, 'Tambahkan contoh kode HTML5 yang ringkas.');
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => {
      submitBtn.click();
    });

    expect(regenSpy).toHaveBeenCalledWith('wf-1', {
      scope: 'ITEM',
      content_id: 'ct-1',
      notes: 'Tambahkan contoh kode HTML5 yang ringkas.',
    });

    await waitFor(() => container.textContent.includes('Draf versi baru (v2) siap direview'), 'New draft banner');
    const reviewLink = [...container.querySelectorAll('a')].find((a) => a.textContent.includes('Buka Tab Review'));
    expect(reviewLink?.getAttribute('href')).toBe('/course/48/ai/review');
  });

  it('tidak menampilkan tombol Regenerasi konten untuk aktivitas manual atau halaman mahasiswa', async () => {
    vi.spyOn(workflowService, 'findWorkflowForCourse').mockResolvedValue({
      id: 'wf-1',
      moodle_course_id: 48,
      status: 'RUNNING',
      stage: 'instructor_review',
    });
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([
      { execution_id: 'exec-full-1', scope: 'FULL', status: 'SUCCESS' },
    ]);
    vi.spyOn(executionService, 'getExecution').mockResolvedValue({
      execution_id: 'exec-full-1',
      scope: 'FULL',
      operations: [],
    });

    await renderDosenActivity(84);
    await waitFor(() => container.textContent.includes('Forum pengumuman manual'), 'Manual forum');
    expect(container.textContent).not.toContain('Regenerasi konten');

    await act(async () => root.unmount());
    await renderMahasiswaActivity(311);
    await waitFor(() => container.textContent.includes('Isi materi dasar web.'), 'Student page');
    expect(container.textContent).not.toContain('Regenerasi konten');
  });
});
