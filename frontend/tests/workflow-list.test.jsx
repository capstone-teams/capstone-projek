import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import WorkflowStatusPage from '../src/pages/dosen/ai/WorkflowStatusPage';
import * as rpsService from '../src/services/rpsService';
import * as workflowService from '../src/services/workflowService';
import { latestWorkflowPerRps } from '../src/utils/workflowList';

// Satu workflow per mata kuliah: RPS yang diunggah ulang membuat workflow baru yang menggantikan yang lama di daftar.
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const wf = (id, rps, created, extra = {}) => ({ id, rps_id: rps, status: 'RUNNING', stage: 'instructor_review', progress: { completed: 2, total: 2 }, created_at: created, updated_at: created, ...extra });
// Sesuai daftar di server: MBD dan SBD masing-masing diunggah dua kali.
const items = [
  wf('wf-fisika', 'rps-fisika', '2026-11-10T13:20:39Z', { progress: { completed: 1, total: 1 } }),
  wf('wf-sbd-2', 'rps-sbd', '2026-11-10T07:28:08Z', { status: 'FAILED', stage: null, progress: { completed: 1, total: 2 } }),
  wf('wf-dw', 'rps-dw', '2026-11-10T06:15:48Z'),
  wf('wf-mbd-2', 'rps-mbd', '2026-11-10T05:27:48Z'),
  wf('wf-sbd-1', 'rps-sbd', '2026-11-09T15:17:33Z'),
  wf('wf-mbd-1', 'rps-mbd', '2026-11-09T15:08:01Z'),
];
const rps = [
  { id: 'rps-fisika', filename: 'RPS Fisika Dasar 1.pdf' },
  { id: 'rps-sbd', filename: 'RPS SBD Genap 2223.pdf' },
  { id: 'rps-dw', filename: 'Desain Web_IF2514501_RPS.pdf' },
  { id: 'rps-mbd', filename: 'RPS MBD 2223.pdf' },
];

describe('satu workflow per mata kuliah (per RPS)', () => {
  it('hanya workflow terbaru tiap RPS yang dipakai, urut terbaru', () => {
    expect(latestWorkflowPerRps(items).map((item) => item.id)).toEqual(['wf-fisika', 'wf-sbd-2', 'wf-dw', 'wf-mbd-2']);
    expect(latestWorkflowPerRps([])).toEqual([]);
  });

  describe('halaman Workflow', () => {
    let node;
    let root;
    beforeEach(() => {
      vi.spyOn(workflowService, 'listWorkflows').mockResolvedValue(items);
      vi.spyOn(workflowService, 'getWorkflow').mockImplementation(async (id) => items.find((item) => item.id === id));
      vi.spyOn(workflowService, 'getWorkflowEvents').mockResolvedValue([]);
      vi.spyOn(rpsService, 'listRps').mockResolvedValue({ items: rps });
      node = document.createElement('div');
      document.body.appendChild(node);
      root = createRoot(node);
    });
    afterEach(async () => {
      await act(async () => root.unmount());
      node.remove();
      vi.restoreAllMocks();
    });
    const render = async (entry = '/') => {
      await act(async () => root.render(<MemoryRouter initialEntries={[entry]}><WorkflowStatusPage /></MemoryRouter>));
      await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
    };
    const listed = () => [...node.querySelectorAll('[aria-label="Daftar workflow"] li')].map((li) => li.querySelector('a').getAttribute('href'));

    it('daftar menampilkan satu workflow per RPS; workflow lama digantikan yang terbaru', async () => {
      await render();
      expect(listed()).toEqual(['/?workflow=wf-fisika', '/?workflow=wf-sbd-2', '/?workflow=wf-dw', '/?workflow=wf-mbd-2']);
      expect(node.querySelector('[aria-label="Daftar workflow"]').textContent.match(/RPS MBD 2223\.pdf/g)).toHaveLength(1);
    });

    // Di Generator AI kursus, layout memberi konteks kursus dan workflow aktifnya.
    const renderInCourse = async (context) => {
      await act(async () => root.render(
        <MemoryRouter initialEntries={['/course/49/ai/workflows']}>
          <Routes>
            <Route path="/course/:courseId/ai" element={<Outlet context={context} />}>
              <Route path="workflows" element={<WorkflowStatusPage />} />
            </Route>
          </Routes>
        </MemoryRouter>,
      ));
      await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
    };

    it('di kursus 49 hanya workflow kursus itu yang tampil (satu kursus satu workflow)', async () => {
      await renderInCourse({ course: { moodle_course_id: 49 }, workflowId: 'wf-fisika' });
      expect(node.textContent).toContain('Workflow kursus ini');
      const names = [...node.querySelectorAll('[aria-label="Daftar workflow"] li')].map((li) => li.textContent);
      expect(names).toHaveLength(1);
      expect(names[0]).toContain('RPS Fisika Dasar 1.pdf');
      expect(node.textContent).not.toContain('Desain Web_IF2514501_RPS.pdf');
    });

    it('selama workflow kursus masih dicari, halaman menunggu (bukan menyatakan kosong)', async () => {
      await renderInCourse({ course: { moodle_course_id: 48 }, workflowId: null, workflowLoading: true });
      expect(node.textContent).toContain('Memuat daftar workflow');
      expect(node.textContent).not.toContain('Kursus ini belum punya workflow.');
    });

    it('kursus tanpa workflow menampilkan keterangan kosong', async () => {
      await renderInCourse({ course: { moodle_course_id: 50 }, workflowId: null });
      expect(node.textContent).toContain('Kursus ini belum punya workflow.');
    });

    it('tautan langsung ke workflow lama tetap membuka detailnya', async () => {
      await render('/?workflow=wf-mbd-1');
      expect(workflowService.getWorkflow).toHaveBeenCalledWith('wf-mbd-1');
      expect(listed()).not.toContain('/?workflow=wf-mbd-1');
    });
  });
});
