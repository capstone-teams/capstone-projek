import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import WorkflowStageList from '../src/components/ai/WorkflowStageList';
import WorkflowStatusBadge from '../src/components/ai/WorkflowStatusBadge';
import WorkflowStatusPanel from '../src/components/ai/WorkflowStatusPanel';
import WorkflowStatusPage from '../src/pages/dosen/ai/WorkflowStatusPage';
import * as workflowService from '../src/services/workflowService';
import * as rpsService from '../src/services/rpsService';
import {
  EVENT_TYPE,
  EVENT_TYPE_META,
  STAGE_STATE,
  WORKFLOW_EVENT,
  WORKFLOW_EVENT_LABELS,
  WORKFLOW_PIPELINE,
  WORKFLOW_STAGE,
  WORKFLOW_STATUS,
  WORKFLOW_STATUS_META,
  deriveStages,
  eventTypeOf,
  needsInstructorAction,
  workflowStatusOf,
} from '../src/utils/workflowStatus';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const wf = (overrides = {}) => ({
  id: 'wf1', status: 'RUNNING', stage: 'rps_analysis', progress: { completed: 1, total: 2 }, rps_id: 'rps1',
  created_at: '2026-11-02T08:00:00Z', updated_at: '2026-11-02T08:01:00Z', ...overrides,
});
const ev = (event, stage, extra = {}) => ({ event, workflow_id: 'wf1', stage, message: `${event} ${stage}`, timestamp: '2026-11-02T08:00:30Z', ...extra });
const stateOf = (stages, stage) => stages.find((s) => s.stage === stage).state;

describe('FE-10.1 konstanta status dan event', () => {
  it('memuat seluruh nilai WorkflowStatus backend dengan label, warna, dan penanda', () => {
    expect(Object.keys(WORKFLOW_STATUS)).toEqual([
      'QUEUED', 'PROCESSING_RPS', 'ANALYZING_RPS', 'PLANNING_COURSE', 'GENERATING_CONTENT', 'VALIDATING',
      'WAITING_FOR_REVIEW', 'EXECUTING_TO_MOODLE', 'VERIFYING', 'RETRYING', 'COMPLETED', 'FAILED',
    ]);
    Object.values(WORKFLOW_STATUS).forEach((status) => {
      expect(WORKFLOW_STATUS_META[status]).toMatchObject({ label: expect.any(String), tone: expect.any(String), marker: expect.any(String) });
    });
  });

  it('FAILED dan RETRYING dibedakan lewat warna dan bentuk penanda', () => {
    const failed = WORKFLOW_STATUS_META[WORKFLOW_STATUS.FAILED];
    const retrying = WORKFLOW_STATUS_META[WORKFLOW_STATUS.RETRYING];
    expect(failed.tone).toBe('danger');
    expect(retrying.tone).toBe('warning');
    expect(failed.marker).not.toBe(retrying.marker);
    expect(failed.label).not.toBe(retrying.label);
  });

  it('menurunkan WorkflowStatus rinci dari status lifecycle dan stage yang dikirim API', () => {
    expect(workflowStatusOf({ status: 'QUEUED', stage: null })).toBe('QUEUED');
    expect(workflowStatusOf({ status: 'COMPLETED', stage: null })).toBe('COMPLETED');
    expect(workflowStatusOf({ status: 'FAILED', stage: null })).toBe('FAILED');
    const byStage = {
      rps_processing: 'PROCESSING_RPS', rps_analysis: 'ANALYZING_RPS', course_planning: 'PLANNING_COURSE',
      content_generation: 'GENERATING_CONTENT', validation: 'VALIDATING', instructor_review: 'WAITING_FOR_REVIEW',
      moodle_execution: 'EXECUTING_TO_MOODLE', verification: 'VERIFYING', retrying: 'RETRYING',
    };
    Object.entries(byStage).forEach(([stage, status]) => expect(workflowStatusOf({ status: 'RUNNING', stage })).toBe(status));
    expect(needsInstructorAction({ status: 'RUNNING', stage: 'instructor_review' })).toBe(true);
    expect(needsInstructorAction({ status: 'RUNNING', stage: 'rps_analysis' })).toBe(false);
  });

  it('memuat kategori EventType dan nama event publik beserta label', () => {
    expect(Object.keys(EVENT_TYPE)).toEqual(['PERUBAHAN_TAHAP', 'AKTIVITAS_AGENT', 'OPERASI_MOODLE', 'RETRY_FIX', 'ERROR_FAILURE']);
    Object.values(EVENT_TYPE).forEach((type) => expect(EVENT_TYPE_META[type].label).toBeTruthy());
    Object.values(WORKFLOW_EVENT).forEach((name) => expect(WORKFLOW_EVENT_LABELS[name]).toBeTruthy());
    expect(eventTypeOf(ev('WORKFLOW_RETRY', 'rps_analysis'))).toBe('RETRY_FIX');
    expect(eventTypeOf(ev('WORKFLOW_FAILED', 'rps_analysis'))).toBe('ERROR_FAILURE');
    expect(eventTypeOf(ev('WORKFLOW_STAGE_PROGRESS', 'rps_analysis'))).toBe('AKTIVITAS_AGENT');
    expect(eventTypeOf(ev('WORKFLOW_STAGE_PROGRESS', 'moodle_execution'))).toBe('OPERASI_MOODLE');
    expect(eventTypeOf(ev('WORKFLOW_STAGE_STARTED', 'rps_analysis'))).toBe('PERUBAHAN_TAHAP');
  });
});

describe('FE-10.1 indikator tahap', () => {
  it('menandai tahap selesai, berjalan, dan menunggu dari data backend', () => {
    const stages = deriveStages(wf(), [
      ev('WORKFLOW_STARTED', null), ev('WORKFLOW_STAGE_STARTED', 'rps_processing'), ev('WORKFLOW_STAGE_COMPLETED', 'rps_processing'),
      ev('WORKFLOW_STAGE_STARTED', 'rps_analysis'),
    ]);
    expect(stages.map((s) => s.stage)).toEqual(WORKFLOW_PIPELINE);
    expect(stateOf(stages, 'rps_processing')).toBe(STAGE_STATE.DONE);
    expect(stateOf(stages, 'rps_analysis')).toBe(STAGE_STATE.RUNNING);
    expect(stateOf(stages, 'course_planning')).toBe(STAGE_STATE.PENDING);
  });

  it('menandai tahap yang menunggu tindakan dosen (WAITING_FOR_REVIEW)', () => {
    const stages = deriveStages(wf({ stage: 'instructor_review' }), [ev('WORKFLOW_STAGE_COMPLETED', 'validation')]);
    expect(stateOf(stages, 'instructor_review')).toBe(STAGE_STATE.REVIEW);
    expect(stateOf(stages, 'validation')).toBe(STAGE_STATE.DONE);
  });

  it('menandai tahap yang sedang dicoba ulang dari event WORKFLOW_RETRY', () => {
    const stages = deriveStages(wf({ stage: 'retrying' }), [ev('WORKFLOW_STAGE_STARTED', 'rps_analysis'), ev('WORKFLOW_RETRY', 'rps_analysis')]);
    expect(stateOf(stages, 'rps_analysis')).toBe(STAGE_STATE.RETRYING);
  });

  it('menandai tahap yang gagal dari event WORKFLOW_FAILED, atau tahap terakhir yang dimulai', () => {
    const failed = wf({ status: 'FAILED', stage: null });
    expect(stateOf(deriveStages(failed, [ev('WORKFLOW_STAGE_STARTED', 'rps_processing'), ev('WORKFLOW_FAILED', 'rps_processing')]), 'rps_processing')).toBe(STAGE_STATE.FAILED);
    expect(stateOf(deriveStages(failed, [ev('WORKFLOW_STAGE_STARTED', 'rps_analysis')]), 'rps_analysis')).toBe(STAGE_STATE.FAILED);
  });

  it('workflow selesai: tahap yang dijalankan selesai, sisanya tidak ditandai berjalan', () => {
    const stages = deriveStages(wf({ status: 'COMPLETED', stage: null }), [ev('WORKFLOW_STAGE_COMPLETED', 'rps_processing'), ev('WORKFLOW_STAGE_COMPLETED', 'rps_analysis')]);
    expect(stages.filter((s) => s.state === STAGE_STATE.DONE).map((s) => s.stage)).toEqual(['rps_processing', 'rps_analysis']);
    expect(stages.some((s) => [STAGE_STATE.RUNNING, STAGE_STATE.FAILED, STAGE_STATE.RETRYING].includes(s.state))).toBe(false);
  });
});

describe('FE-10.1 tampilan status', () => {
  let container;
  let root;
  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });
  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.restoreAllMocks();
  });
  const show = (node) => act(async () => root.render(<MemoryRouter>{node}</MemoryRouter>));

  it('badge FAILED dan RETRYING berbeda secara visual (warna, penanda, dan teks)', async () => {
    await show(<><WorkflowStatusBadge workflow={wf({ status: 'FAILED', stage: null })} /><WorkflowStatusBadge workflow={wf({ stage: 'retrying' })} /></>);
    const [failed, retrying] = [...container.querySelectorAll('[data-marker]')];
    expect(failed.dataset.marker).toBe('failed');
    expect(retrying.dataset.marker).toBe('retry');
    expect(failed.textContent).toContain('✕');
    expect(retrying.textContent).toContain('↻');
    expect(failed.parentElement.className).not.toBe(retrying.parentElement.className);
  });

  it('panel menampilkan peringatan tindakan dosen, percobaan ulang, dan kegagalan dengan pesan backend', async () => {
    await show(<WorkflowStatusPanel workflow={wf({ stage: 'instructor_review' })} events={[]} />);
    expect(container.textContent).toContain('Menunggu tindakan Anda');
    expect(container.querySelector('[data-stage="instructor_review"]').dataset.state).toBe('review');

    await show(<WorkflowStatusPanel workflow={wf({ stage: 'retrying' })} events={[ev('WORKFLOW_RETRY', 'rps_analysis', { message: 'Memperbaiki keluaran model.' })]} />);
    expect(container.textContent).toContain('Mencoba ulang');
    expect(container.textContent).toContain('Memperbaiki keluaran model.');
    expect(container.querySelector('[data-stage="rps_analysis"]').dataset.state).toBe('retrying');

    await show(<WorkflowStatusPanel workflow={wf({ status: 'FAILED', stage: null })} events={[ev('WORKFLOW_FAILED', 'rps_analysis', { message: 'Analisis RPS gagal.' })]} />);
    expect(container.querySelector('[role="alert"]').textContent).toContain('Analisis RPS gagal.');
    expect(container.querySelector('[data-stage="rps_analysis"]').dataset.state).toBe('failed');
    expect(container.textContent).not.toContain('Mencoba ulang');
  });

  it('daftar tahap tampil lengkap tanpa menyebut tahap belum dijalankan sebagai "Menunggu" pada workflow selesai', async () => {
    await show(<WorkflowStageList workflow={wf({ status: 'COMPLETED', stage: null })} events={[ev('WORKFLOW_STAGE_COMPLETED', 'rps_analysis')]} />);
    expect(container.querySelectorAll('li')).toHaveLength(WORKFLOW_PIPELINE.length);
    expect(container.querySelector('[data-stage="course_planning"]').textContent).toContain('Belum dijalankan');
  });

  it('halaman menampilkan daftar dari GET /workflows dan detail dari GET /workflows/{id}, lalu berpindah workflow', async () => {
    const items = [
      wf({ id: 'wfA', rps_id: 'rpsA', stage: 'rps_analysis' }),
      wf({ id: 'wfB', rps_id: 'rpsB', status: 'FAILED', stage: null, progress: { completed: 0, total: 2 } }),
    ];
    vi.spyOn(workflowService, 'listWorkflows').mockResolvedValue(items);
    const detail = vi.spyOn(workflowService, 'getWorkflow').mockImplementation(async (id) => items.find((item) => item.id === id));
    vi.spyOn(workflowService, 'getWorkflowEvents').mockResolvedValue([]);
    vi.spyOn(rpsService, 'listRps').mockResolvedValue({ items: [{ id: 'rpsA', filename: 'RPS-A.pdf' }, { id: 'rpsB', filename: 'RPS-B.pdf' }] });
    await show(<WorkflowStatusPage />);
    await act(() => new Promise((resolve) => setTimeout(resolve, 30)));

    const rows = [...container.querySelectorAll('ul[aria-label="Daftar workflow"] > li')];
    expect(rows).toHaveLength(2);
    expect(rows[0].textContent).toContain('RPS-A.pdf');
    expect(rows[0].textContent).toContain('Menganalisis RPS');
    expect(rows[1].textContent).toContain('Gagal');
    expect(rows[1].textContent).toContain('Berhenti karena kesalahan');
    expect(rows[1].textContent).not.toContain('Selesai diproses');
    expect(detail).toHaveBeenCalledWith('wfA');
    expect(container.querySelector('[data-stage="rps_analysis"]').dataset.state).toBe('running');

    await act(async () => rows[1].querySelector('a').click());
    await act(() => new Promise((resolve) => setTimeout(resolve, 30)));
    expect(detail).toHaveBeenCalledWith('wfB');
    expect(container.textContent).toContain('Workflow gagal');
  });

  it('status berubah otomatis lewat polling sampai selesai, lalu berhenti memanggil API', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      let current = wf({ id: 'wfA', stage: 'rps_analysis' });
      vi.spyOn(workflowService, 'listWorkflows').mockImplementation(async () => [current]);
      const detail = vi.spyOn(workflowService, 'getWorkflow').mockImplementation(async () => current);
      vi.spyOn(workflowService, 'getWorkflowEvents').mockResolvedValue([]);
      vi.spyOn(rpsService, 'listRps').mockResolvedValue({ items: [] });
      await show(<WorkflowStatusPage />);
      await act(async () => { await vi.advanceTimersByTimeAsync(50); });
      expect(container.querySelector('[data-stage="rps_analysis"]').dataset.state).toBe('running');

      current = wf({ id: 'wfA', status: 'COMPLETED', stage: null, progress: { completed: 2, total: 2 } });
      await act(async () => { await vi.advanceTimersByTimeAsync(6000); });
      expect(container.querySelector('[data-marker="done"]')).not.toBeNull();
      const calls = detail.mock.calls.length;
      await act(async () => { await vi.advanceTimersByTimeAsync(20000); });
      expect(detail.mock.calls.length).toBe(calls);
    } finally {
      vi.useRealTimers();
    }
  });

  it('menampilkan keadaan kosong bila belum ada workflow', async () => {
    vi.spyOn(workflowService, 'listWorkflows').mockResolvedValue([]);
    vi.spyOn(rpsService, 'listRps').mockResolvedValue({ items: [] });
    await show(<WorkflowStatusPage />);
    await act(() => new Promise((resolve) => setTimeout(resolve, 30)));
    expect(container.textContent).toContain('Belum ada workflow.');
  });
});
