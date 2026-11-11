import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import WorkflowContentProgress from '../src/components/ai/WorkflowContentProgress';
import WorkflowMoodleOperations from '../src/components/ai/WorkflowMoodleOperations';
import WorkflowStatusPanel from '../src/components/ai/WorkflowStatusPanel';
import { CONTENT_STATE, contentGenerationProgress, parseContentMessage } from '../src/utils/contentEvents';
import { AWAITED_ACTION, STAGE_STATE, awaitedActionOf, coursePlanFailureOf, deriveStages, eventTypeOf } from '../src/utils/workflowStatus';

// FE-19.1: monitoring tahap M04 (pembuatan dan validasi konten, review konten, eksekusi FULL). Pesan event mengikuti
// format backend (orchestrator._content_emitter, ContentGenerationService, ExecutionService).
const executions = vi.hoisted(() => ({ getLatestWorkflowExecution: vi.fn() }));
vi.mock('../src/services/executionService', async (original) => ({ ...(await original()), ...executions }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

let clock = 0;
const ev = (event, stage = null, message = '') => {
  clock += 1;
  return { event, stage, message, workflow_id: 'wf1', timestamp: `2026-11-10T09:${String(Math.floor(clock / 60)).padStart(2, '0')}:${String(clock % 60).padStart(2, '0')}Z` };
};
const wf = (overrides = {}) => ({ id: 'wf1', status: 'RUNNING', stage: 'instructor_review', rps_id: 'rps1', updated_at: '2026-11-10T08:00:00Z', ...overrides });

// Riwayat event dari backend, berurutan.
const planned = () => [ev('WORKFLOW_STAGE_STARTED', 'course_planning'), ev('WORKFLOW_STAGE_COMPLETED', 'course_planning'), ev('WORKFLOW_STAGE_STARTED', 'validation'), ev('WORKFLOW_PLAN_GENERATED', 'validation'), ev('WORKFLOW_STAGE_COMPLETED', 'validation'), ev('WORKFLOW_WAITING_FOR_REVIEW', 'instructor_review')];
const generating = () => [
  ...planned(), ev('WORKFLOW_PLAN_APPROVED', 'instructor_review'),
  ev('WORKFLOW_STAGE_STARTED', 'content_generation'),
  ev('WORKFLOW_STAGE_PROGRESS', 'content_generation', 'Minggu 1 - Learning Material dimulai.'),
  ev('WORKFLOW_STAGE_PROGRESS', 'content_generation', 'Minggu 1 - Learning Material selesai.'),
  ev('WORKFLOW_STAGE_PROGRESS', 'content_generation', 'Minggu 1 - Quiz sedang dihasilkan.'),
  ev('WORKFLOW_RETRY', 'content_generation', 'Minggu 1 - Quiz diperbaiki.'),
  ev('WORKFLOW_STAGE_PROGRESS', 'content_generation', 'Minggu 2 - Assignment gagal.'),
];
const generated = () => [
  ...generating(),
  ev('WORKFLOW_STAGE_PROGRESS', 'content_generation', 'Minggu 1 - Quiz selesai.'),
  ev('WORKFLOW_STAGE_COMPLETED', 'content_generation'),
  ev('WORKFLOW_STAGE_STARTED', 'validation'),
  ev('WORKFLOW_CONTENT_VALIDATED', 'validation', 'Minggu 1 - Learning Material selesai.'),
  ev('WORKFLOW_CONTENT_VALIDATION_FAILED', 'validation', 'Minggu 1 - Quiz gagal validasi.'),
  ev('WORKFLOW_WEEK_COMPLETED', 'validation', 'Minggu 1 selesai: 1 konten berhasil divalidasi, 1 gagal.'),
  ev('WORKFLOW_STAGE_COMPLETED', 'validation'),
  ev('WORKFLOW_WAITING_FOR_REVIEW', 'instructor_review'),
];

describe('FE-19.1 event konten', () => {
  it('membaca minggu, jenis, dan kejadian dari pesan event konten dan operasi activity', () => {
    expect(parseContentMessage('Minggu 3 - Learning Material diperbaiki.')).toEqual({ week: 3, kind: 'LEARNING_MATERIAL', action: 'diperbaiki' });
    expect(parseContentMessage('Minggu 4 - Quiz diterapkan ke Moodle.')).toEqual({ week: 4, kind: 'QUIZ', action: 'diterapkan ke Moodle' });
    expect(parseContentMessage('Minggu 1 diterapkan ke Moodle.')).toBeNull();
  });

  it('progres GENERATING_CONTENT per minggu × jenis dari run terakhir', () => {
    expect(contentGenerationProgress(planned())).toBeNull();
    const running = contentGenerationProgress(generating());
    expect(running.weeks).toEqual([
      { week: 1, items: [{ kind: 'LEARNING_MATERIAL', state: CONTENT_STATE.GENERATED }, { kind: 'QUIZ', state: CONTENT_STATE.RETRYING }], summary: null },
      { week: 2, items: [{ kind: 'ASSIGNMENT', state: CONTENT_STATE.FAILED }], summary: null },
    ]);
    const done = contentGenerationProgress(generated());
    expect(done.weeks[0]).toEqual({ week: 1, items: [{ kind: 'LEARNING_MATERIAL', state: CONTENT_STATE.VALIDATED }, { kind: 'QUIZ', state: CONTENT_STATE.INVALID }], summary: { validated: 1, failed: 1 } });
    expect(done.weeksDone).toBe(1);
  });

  it('tahap pembuatan konten tampil pada indikator tahap', () => {
    const stages = deriveStages(wf({ stage: 'content_generation' }), generating());
    expect(stages.find((s) => s.stage === 'content_generation')).toMatchObject({ label: 'Pembuatan konten', state: STAGE_STATE.RUNNING });
    expect(eventTypeOf(ev('WORKFLOW_CONTENT_VALIDATION_FAILED', 'validation'))).toBe('ERROR_FAILURE');
  });

  it('validasi konten tidak dibaca sebagai kegagalan atau review course plan', () => {
    const failed = [...generating(), ev('WORKFLOW_STAGE_STARTED', 'validation'), ev('WORKFLOW_FAILED', 'validation', 'Validasi konten gagal.')];
    expect(coursePlanFailureOf(wf({ status: 'FAILED', stage: null }), failed)).toBeNull();
    expect(awaitedActionOf(wf(), generated())).toBe(AWAITED_ACTION.REVIEW_CONTENT);
    expect(awaitedActionOf(wf(), planned())).toBe(AWAITED_ACTION.REVIEW_PLAN);
  });

  it('tindakan yang ditunggu: review konten, regenerasi konten, dan eksekusi FULL', () => {
    expect(awaitedActionOf(wf(), [...generated(), ev('WORKFLOW_CONTENTS_REJECTED', 'instructor_review')])).toBe(AWAITED_ACTION.REVISE_CONTENT);
    expect(awaitedActionOf(wf(), [...generated(), ev('WORKFLOW_CONTENTS_APPROVED', 'instructor_review')])).toBe(AWAITED_ACTION.EXECUTE_FULL);
    // Operasi section (eksekusi struktur) tetap menunggu generate konten; operasi activity (FULL) menunggu verifikasi.
    expect(awaitedActionOf(wf(), [ev('WORKFLOW_MOODLE_OPERATION', 'moodle_execution', 'Minggu 1 diterapkan ke Moodle.')])).toBe(AWAITED_ACTION.GENERATE_CONTENT);
    expect(awaitedActionOf(wf(), [ev('WORKFLOW_MOODLE_OPERATION', 'moodle_execution', 'Minggu 1 - Quiz diterapkan ke Moodle.')])).toBe(AWAITED_ACTION.VERIFY_MOODLE);
  });
});

describe('FE-19.1 tampilan monitoring', () => {
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
  const showPanel = (workflow, events) => act(async () => root.render(
    <MemoryRouter initialEntries={['/course/2/ai/workflows']}>
      <Routes><Route path="/course/:courseId/ai/workflows" element={<WorkflowStatusPanel workflow={workflow} events={events} linkBase=".." />} /></Routes>
    </MemoryRouter>,
  ));

  it('progres pembuatan konten per minggu tampil dan diperbarui bersama event', async () => {
    await act(async () => root.render(<WorkflowContentProgress events={generating()} />));
    const week1 = node.querySelector('li[aria-label="Minggu 1"]');
    expect(week1.textContent).toContain('Materi pembelajaran:Selesai dibuat');
    expect(week1.textContent).toContain('Kuis:Diperbaiki');
    expect(node.querySelector('li[aria-label="Minggu 2"]').textContent).toContain('Tugas:Gagal');
    await act(async () => root.render(<WorkflowContentProgress events={generated()} />));
    expect(node.querySelector('li[aria-label="Minggu 1"]').textContent).toContain('1 lolos, 1 gagal');
    expect(node.querySelector('[role="progressbar"]').getAttribute('aria-valuenow')).toBe('50');
  });

  it('detail RETRY_FIX konten memuat minggu dan jenis', async () => {
    await showPanel(wf({ stage: 'retrying' }), generating());
    expect(node.textContent).toContain('Mencoba ulang: Minggu 1 · Kuis');
    expect(node.textContent).toContain('Minggu 1 - Quiz diperbaiki.');
  });

  it('menunggu review konten: tautan cepat ke halaman Review', async () => {
    await showPanel(wf(), generated());
    expect(node.textContent).toContain('Menunggu tindakan Anda: Review konten');
    const link = [...node.querySelectorAll('a')].find((a) => a.textContent === 'Buka halaman Review');
    expect(link.getAttribute('href')).toBe('/course/2/ai/review');
  });

  it('konten disetujui: menunggu eksekusi FULL dengan tautan ke halaman eksekusi dan Review', async () => {
    await showPanel(wf(), [...generated(), ev('WORKFLOW_CONTENTS_APPROVED', 'instructor_review')]);
    expect(node.textContent).toContain('Menunggu tindakan Anda: Eksekusi FULL');
    const links = Object.fromEntries([...node.querySelectorAll('a')].map((a) => [a.textContent, a.getAttribute('href')]));
    expect(links['Buka halaman eksekusi FULL']).toBe('/course/2/ai/publish');
    expect(links['Buka halaman Review']).toBe('/course/2/ai/review');
  });

  it('detail OPERASI_MOODLE eksekusi FULL: cakupan dan operasi activity per minggu', async () => {
    executions.getLatestWorkflowExecution.mockResolvedValue({
      execution_id: 'ex2', scope: 'FULL', status: 'SUCCESS', summary: { total: 3, success: 2, failed: 0, skipped: 1 },
      operations: [
        { operation_id: 'o1', operation_type: 'SECTION', status: 'SUCCESS', week_number: 1, retry_count: 0 },
        { operation_id: 'o2', operation_type: 'QUIZ', status: 'SUCCESS', week_number: 1, retry_count: 0 },
        { operation_id: 'o3', operation_type: 'ASSIGNMENT', status: 'SKIPPED', week_number: 1, retry_count: 0 },
      ],
    });
    await act(async () => root.render(<WorkflowMoodleOperations workflowId="wf1" events={[ev('WORKFLOW_MOODLE_OPERATION', 'moodle_execution', 'Minggu 1 - Quiz diterapkan ke Moodle.')]} />));
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
    expect(node.textContent).toContain('Cakupan: FULL (struktur dan seluruh konten)');
    const rows = [...node.querySelectorAll('tbody tr')].map((row) => [...row.children].slice(0, 3).map((cell) => cell.textContent));
    expect(rows).toEqual([['Section mingguan', '1', 'Berhasil'], ['Kuis', '1', 'Berhasil'], ['Tugas', '1', 'Dilewati']]);
  });
});
