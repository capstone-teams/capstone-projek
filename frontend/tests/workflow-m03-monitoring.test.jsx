import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import WorkflowMoodleOperations from '../src/components/ai/WorkflowMoodleOperations';
import WorkflowStatusPanel from '../src/components/ai/WorkflowStatusPanel';
import {
  AWAITED_ACTION,
  EVENT_TYPE,
  STAGE_STATE,
  WORKFLOW_PIPELINE,
  applyWorkflowEvent,
  awaitedActionOf,
  deriveStages,
  eventTypeOf,
} from '../src/utils/workflowStatus';

// Monitoring workflow untuk tahap M03: course planning, validasi, review dosen, dan eksekusi struktur ke Moodle.
const executions = vi.hoisted(() => ({ getLatestWorkflowExecution: vi.fn() }));
vi.mock('../src/services/executionService', async (original) => ({ ...(await original()), ...executions }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const wf = (overrides = {}) => ({ id: 'wf1', status: 'RUNNING', stage: 'instructor_review', rps_id: 'rps1', updated_at: '2026-11-09T08:00:00Z', ...overrides });
let clock = 0;
const ev = (event, stage = null, message = '') => {
  clock += 1;
  return { event, stage, message, workflow_id: 'wf1', timestamp: `2026-11-09T08:${String(clock).padStart(2, '0')}:00Z` };
};
const stateOf = (stages, stage) => stages.find((s) => s.stage === stage)?.state;

// Riwayat event M03 dari backend, berurutan.
const analyzed = () => [ev('WORKFLOW_STAGE_STARTED', 'rps_processing'), ev('WORKFLOW_STAGE_COMPLETED', 'rps_processing'), ev('WORKFLOW_STAGE_STARTED', 'rps_analysis'), ev('WORKFLOW_STAGE_COMPLETED', 'rps_analysis'), ev('WORKFLOW_WAITING_FOR_REVIEW', 'instructor_review')];
const planned = () => [...analyzed(), ev('WORKFLOW_STAGE_STARTED', 'course_planning'), ev('WORKFLOW_STAGE_COMPLETED', 'course_planning'), ev('WORKFLOW_STAGE_STARTED', 'validation'), ev('WORKFLOW_PLAN_GENERATED', 'validation'), ev('WORKFLOW_STAGE_COMPLETED', 'validation'), ev('WORKFLOW_WAITING_FOR_REVIEW', 'instructor_review')];
const approved = () => [...planned(), ev('WORKFLOW_PLAN_APPROVED', 'instructor_review')];
const executing = () => [...approved(), ev('WORKFLOW_STAGE_STARTED', 'moodle_execution'), ev('WORKFLOW_MOODLE_OPERATION', 'moodle_execution', 'Minggu 1 diterapkan ke Moodle.')];
const executed = () => [...executing(), ev('WORKFLOW_STAGE_COMPLETED', 'moodle_execution'), ev('WORKFLOW_WAITING_FOR_REVIEW', 'instructor_review')];

describe('FE-10.4 tahap M03 pada monitoring', () => {
  it('urutan tahap mencakup PLANNING_COURSE, VALIDATING, WAITING_FOR_REVIEW, dan EXECUTING_TO_MOODLE', () => {
    // M04 menambahkan pembuatan konten sebelum eksekusi (FE-19.1).
    expect(WORKFLOW_PIPELINE).toEqual(['rps_processing', 'rps_analysis', 'course_planning', 'validation', 'instructor_review', 'content_generation', 'moodle_execution']);
    const labels = deriveStages(wf(), []).map((s) => s.label);
    expect(labels).toEqual(['Pemrosesan RPS', 'Analisis RPS', 'Penyusunan rencana', 'Validasi', 'Review dosen', 'Pembuatan konten', 'Eksekusi ke Moodle']);
  });

  it('menandai keadaan tiap tahap M03 dari status dan event', () => {
    let stages = deriveStages(wf({ stage: 'validation' }), [...analyzed(), ev('WORKFLOW_STAGE_STARTED', 'course_planning'), ev('WORKFLOW_STAGE_COMPLETED', 'course_planning')]);
    expect(stateOf(stages, 'course_planning')).toBe(STAGE_STATE.DONE);
    expect(stateOf(stages, 'validation')).toBe(STAGE_STATE.RUNNING);

    stages = deriveStages(wf(), planned());
    expect(stateOf(stages, 'validation')).toBe(STAGE_STATE.DONE);
    expect(stateOf(stages, 'instructor_review')).toBe(STAGE_STATE.REVIEW);

    // Eksekusi berjalan setelah review: review dosen sudah selesai.
    stages = deriveStages(wf({ stage: 'moodle_execution' }), executing());
    expect(stateOf(stages, 'instructor_review')).toBe(STAGE_STATE.DONE);
    expect(stateOf(stages, 'moodle_execution')).toBe(STAGE_STATE.RUNNING);
  });

  it('event eksekusi dan keputusan rencana diterapkan real-time ke status workflow', () => {
    const base = wf({ updated_at: '2026-11-09T07:00:00Z' });
    expect(applyWorkflowEvent(base, ev('WORKFLOW_MOODLE_OPERATION', 'moodle_execution'))).toMatchObject({ status: 'RUNNING', stage: 'moodle_execution' });
    const decided = applyWorkflowEvent(base, ev('WORKFLOW_PLAN_APPROVED', 'instructor_review'));
    expect(decided.stage).toBe('instructor_review');
    expect(decided.updated_at).not.toBe(base.updated_at);
    expect(eventTypeOf(ev('WORKFLOW_MOODLE_OPERATION', 'moodle_execution'))).toBe(EVENT_TYPE.OPERASI_MOODLE);
  });

  it('tindakan yang ditunggu pada WAITING_FOR_REVIEW dibaca dari event terakhir', () => {
    expect(awaitedActionOf(wf(), analyzed())).toBe(AWAITED_ACTION.START_PLANNING);
    expect(awaitedActionOf(wf(), planned())).toBe(AWAITED_ACTION.REVIEW_PLAN);
    expect(awaitedActionOf(wf(), [...planned(), ev('WORKFLOW_PLAN_REJECTED', 'instructor_review')])).toBe(AWAITED_ACTION.REVISE_PLAN);
    expect(awaitedActionOf(wf(), approved())).toBe(AWAITED_ACTION.EXECUTE_STRUCTURE);
    expect(awaitedActionOf(wf(), executed())).toBe(AWAITED_ACTION.GENERATE_CONTENT);
    expect(awaitedActionOf(wf({ stage: 'moodle_execution' }), executing())).toBeNull();
  });
});

describe('FE-10.4 tampilan monitoring', () => {
  let node;
  let root;
  beforeEach(() => {
    vi.resetAllMocks();
    node = document.createElement('div');
    document.body.appendChild(node);
    root = createRoot(node);
  });
  afterEach(async () => {
    await act(async () => root.unmount());
    node.remove();
  });
  const showPanel = (workflow, events, linkBase = '..') => act(async () => root.render(
    <MemoryRouter initialEntries={['/course/2/ai/workflows']}>
      <Routes><Route path="/course/:courseId/ai/workflows" element={<WorkflowStatusPanel workflow={workflow} events={events} linkBase={linkBase} />} /></Routes>
    </MemoryRouter>,
  ));
  const quickLink = () => node.querySelector('[role="status"] a');

  it('menunggu review course plan: keterangan dan tautan cepat ke Plan Review workflow ini', async () => {
    await showPanel(wf(), planned());
    expect(node.textContent).toContain('Menunggu tindakan Anda: Review course plan');
    expect(quickLink().textContent).toBe('Buka Plan Review');
    expect(quickLink().getAttribute('href')).toBe('/course/2/ai/plan?workflow=wf1&rps=rps1');
  });

  it('rencana disetujui: menunggu eksekusi struktur dengan tautan ke halaman eksekusi', async () => {
    await showPanel(wf(), approved());
    expect(node.textContent).toContain('Menunggu tindakan Anda: Eksekusi struktur');
    expect(quickLink().textContent).toBe('Buka halaman eksekusi');
    expect(quickLink().getAttribute('href')).toBe('/course/2/ai/publish');
  });

  it('eksekusi struktur selesai: menunggu generate konten dengan tautan ke halaman Konten (FE-16)', async () => {
    await showPanel(wf(), executed());
    expect(node.textContent).toContain('Menunggu tindakan Anda: Generate konten');
    expect(quickLink().getAttribute('href')).toBe('/course/2/ai/content');
  });

  it('tanpa linkBase keterangan tetap tampil tanpa tautan', async () => {
    await showPanel(wf(), planned(), null);
    expect(node.textContent).toContain('Review course plan');
    expect(quickLink()).toBeNull();
  });

  const execution = (operations, overrides = {}) => ({
    execution_id: 'ex1', workflow_id: 'wf1', scope: 'STRUCTURE', status: 'RUNNING', moodle_course_id: 42,
    summary: { total: 3, success: 1, failed: 1, skipped: 0 }, operations, ...overrides,
  });
  const showOperations = (events) => act(async () => root.render(<WorkflowMoodleOperations workflowId="wf1" events={events} />));

  it('detail OPERASI_MOODLE: jenis operasi, minggu, dan status tiap operasi eksekusi terbaru', async () => {
    executions.getLatestWorkflowExecution.mockResolvedValue(execution([
      { operation_id: 'op2', operation_type: 'SECTION', status: 'FAILED', week_number: 2, error_message: 'Moodle menolak nama section.', retry_count: 0 },
      { operation_id: 'op1', operation_type: 'SECTION', status: 'SUCCESS', week_number: 1, retry_count: 0 },
      { operation_id: 'op3', operation_type: 'SECTION', status: 'PENDING', week_number: 3, retry_count: 0 },
    ]));
    await showOperations(executing());
    expect(executions.getLatestWorkflowExecution).toHaveBeenCalledWith('wf1');
    const rows = [...node.querySelectorAll('tbody tr')].map((row) => [...row.children].map((cell) => cell.textContent));
    expect(rows).toEqual([
      ['Section mingguan', '1', 'Berhasil', ''],
      ['Section mingguan', '2', 'Gagal', 'Moodle menolak nama section.'],
      ['Section mingguan', '3', 'Menunggu', ''],
    ]);
    expect(node.textContent).toContain('1 berhasil · 1 gagal · 0 dilewati dari 3 operasi');
  });

  it('event operasi baru memuat ulang detail eksekusi (real-time)', async () => {
    executions.getLatestWorkflowExecution.mockResolvedValue(execution([]));
    const events = executing();
    await showOperations(events);
    expect(executions.getLatestWorkflowExecution).toHaveBeenCalledTimes(1);
    await showOperations([...events, ev('WORKFLOW_MOODLE_OPERATION', 'moodle_execution', 'Minggu 2 diterapkan ke Moodle.')]);
    await act(() => new Promise((resolve) => setTimeout(resolve, 350)));
    expect(executions.getLatestWorkflowExecution).toHaveBeenCalledTimes(2);
  });

  it('workflow yang belum masuk tahap eksekusi tidak memanggil endpoint eksekusi', async () => {
    await showOperations(planned());
    expect(executions.getLatestWorkflowExecution).not.toHaveBeenCalled();
    expect(node.textContent).toBe('');
  });
});
