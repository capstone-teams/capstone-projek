import { describe, expect, it } from 'vitest';
import { appStateReducer, initialAppState } from '../src/state/appState';
import {
  MAX_WORKFLOW_EVENTS,
  applyWorkflowEvent,
  eventKey,
  isFinalWorkflowEvent,
  mergeEvents,
} from '../src/utils/workflowStatus';

const wf = (overrides = {}) => ({
  id: 'wf1', status: 'RUNNING', stage: 'rps_processing', progress: { completed: 0, total: 2 }, rps_id: 'rps1',
  created_at: '2026-11-02T08:00:00Z', updated_at: '2026-11-02T08:00:00Z', moodle_course_id: null, ...overrides,
});
const ev = (event, stage, second, extra = {}) => ({
  event, workflow_id: 'wf1', stage, progress: { completed: 0, total: 2 }, message: `${event} ${stage}`,
  timestamp: `2026-11-02T08:00:${String(second).padStart(2, '0')}Z`, ...extra,
});

describe('FE-10.2 menerapkan event ke status workflow', () => {
  it('WORKFLOW_STARTED dan event tahap menjadikan workflow berjalan pada tahap itu', () => {
    const queued = wf({ status: 'QUEUED', stage: null });
    expect(applyWorkflowEvent(queued, ev('WORKFLOW_STARTED', null, 5))).toMatchObject({ status: 'RUNNING', updated_at: '2026-11-02T08:00:05Z' });
    const started = applyWorkflowEvent(queued, ev('WORKFLOW_STAGE_STARTED', 'rps_analysis', 6, { progress: { completed: 1, total: 2 } }));
    expect(started).toMatchObject({ status: 'RUNNING', stage: 'rps_analysis', progress: { completed: 1, total: 2 } });
    expect(applyWorkflowEvent(started, ev('WORKFLOW_STAGE_PROGRESS', 'rps_analysis', 7))).toMatchObject({ stage: 'rps_analysis' });
  });

  it('WORKFLOW_RETRY menandai percobaan ulang, WORKFLOW_COMPLETED dan WORKFLOW_FAILED mengakhiri workflow', () => {
    const running = wf({ stage: 'rps_analysis' });
    expect(applyWorkflowEvent(running, ev('WORKFLOW_RETRY', 'rps_analysis', 9))).toMatchObject({ status: 'RUNNING', stage: 'retrying' });
    expect(applyWorkflowEvent(running, ev('WORKFLOW_COMPLETED', null, 9, { progress: { completed: 2, total: 2 } })))
      .toMatchObject({ status: 'COMPLETED', stage: null, progress: { completed: 2, total: 2 } });
    expect(applyWorkflowEvent(running, ev('WORKFLOW_FAILED', 'rps_analysis', 9))).toMatchObject({ status: 'FAILED', stage: null });
  });

  it('event lama yang sudah tercermin di snapshot dilewati, dan event tak dikenal tidak mengubah apa pun', () => {
    const snapshot = wf({ status: 'FAILED', stage: null, updated_at: '2026-11-02T08:00:30Z' });
    expect(applyWorkflowEvent(snapshot, ev('WORKFLOW_STAGE_STARTED', 'rps_analysis', 10))).toBe(snapshot);
    expect(applyWorkflowEvent(snapshot, ev('WORKFLOW_SOMETHING_ELSE', null, 40))).toBe(snapshot);
    expect(applyWorkflowEvent(null, ev('WORKFLOW_STARTED', null, 1))).toBeNull();
  });

  it('workflow yang dijalankan ulang kembali berjalan saat event baru tiba', () => {
    const failed = wf({ status: 'FAILED', stage: null, updated_at: '2026-11-02T08:00:30Z' });
    expect(applyWorkflowEvent(failed, ev('WORKFLOW_STARTED', null, 45))).toMatchObject({ status: 'RUNNING' });
  });

  it('mengenali event akhir', () => {
    expect(isFinalWorkflowEvent(ev('WORKFLOW_COMPLETED', null, 1))).toBe(true);
    expect(isFinalWorkflowEvent(ev('WORKFLOW_FAILED', null, 1))).toBe(true);
    expect(isFinalWorkflowEvent(ev('WORKFLOW_STAGE_STARTED', 'x', 1))).toBe(false);
    expect(isFinalWorkflowEvent(undefined)).toBe(false);
  });
});

describe('FE-10.2 menggabungkan event', () => {
  it('membuang duplikat antara riwayat HTTP dan frame WebSocket, dan mengurutkan menurut waktu', () => {
    const http = [ev('WORKFLOW_STARTED', null, 1), ev('WORKFLOW_STAGE_STARTED', 'rps_processing', 2)];
    const live = [ev('WORKFLOW_STAGE_STARTED', 'rps_processing', 2), ev('WORKFLOW_STAGE_COMPLETED', 'rps_processing', 3)];
    expect(mergeEvents(live, http).map((event) => event.event)).toEqual(['WORKFLOW_STARTED', 'WORKFLOW_STAGE_STARTED', 'WORKFLOW_STAGE_COMPLETED']);
  });

  it('mempertahankan urutan semula untuk event dengan waktu sama dan membatasi jumlah yang disimpan', () => {
    const same = [ev('WORKFLOW_STAGE_PROGRESS', 'a', 1, { message: 'satu' }), ev('WORKFLOW_STAGE_PROGRESS', 'a', 1, { message: 'dua' })];
    expect(mergeEvents([], same).map((event) => event.message)).toEqual(['satu', 'dua']);
    const many = Array.from({ length: MAX_WORKFLOW_EVENTS + 20 }, (_, index) => ev('WORKFLOW_STAGE_PROGRESS', 'a', 0, { message: `m${index}`, timestamp: new Date(Date.UTC(2026, 10, 2, 8, 0, 0) + index * 1000).toISOString() }));
    const merged = mergeEvents([], many);
    expect(merged).toHaveLength(MAX_WORKFLOW_EVENTS);
    expect(merged.at(-1).message).toBe(`m${MAX_WORKFLOW_EVENTS + 19}`);
    expect(eventKey(merged[0])).not.toBe(eventKey(merged[1]));
  });
});

describe('FE-10.2 state aplikasi (slice workflows)', () => {
  const reduce = (state, ...actions) => actions.reduce(appStateReducer, state);

  it('menyimpan snapshot HTTP lalu menerapkan event WebSocket yang masuk', () => {
    let state = reduce(initialAppState, { type: 'workflow/loaded', id: 'wf1', workflow: wf(), events: [ev('WORKFLOW_STARTED', null, 1)] });
    expect(state.workflows.wf1).toMatchObject({ workflow: { status: 'RUNNING', stage: 'rps_processing' }, connection: 'connecting' });
    state = reduce(state, { type: 'workflow/event', id: 'wf1', event: ev('WORKFLOW_STAGE_STARTED', 'rps_analysis', 20) });
    expect(state.workflows.wf1.workflow.stage).toBe('rps_analysis');
    expect(state.workflows.wf1.events.map((event) => event.event)).toEqual(['WORKFLOW_STARTED', 'WORKFLOW_STAGE_STARTED']);
  });

  it('event yang sama diterima dua kali tidak mengubah state', () => {
    const state = reduce(initialAppState, { type: 'workflow/loaded', id: 'wf1', workflow: wf(), events: [] }, { type: 'workflow/event', id: 'wf1', event: ev('WORKFLOW_STAGE_STARTED', 'rps_analysis', 20) });
    expect(appStateReducer(state, { type: 'workflow/event', id: 'wf1', event: ev('WORKFLOW_STAGE_STARTED', 'rps_analysis', 20) })).toBe(state);
  });

  it('event yang tiba sebelum snapshot diterapkan di atas snapshot yang lebih lama', () => {
    // Frame WebSocket datang saat GET /workflows/{id} masih berjalan; jawabannya lebih lama dari frame itu.
    let state = reduce(initialAppState, { type: 'workflow/event', id: 'wf1', event: ev('WORKFLOW_FAILED', 'rps_analysis', 50) });
    expect(state.workflows.wf1.workflow).toBeNull();
    state = reduce(state, { type: 'workflow/loaded', id: 'wf1', workflow: wf({ stage: 'rps_analysis', updated_at: '2026-11-02T08:00:40Z' }), events: [ev('WORKFLOW_STARTED', null, 1)] });
    expect(state.workflows.wf1.workflow).toMatchObject({ status: 'FAILED', stage: null });
    expect(state.workflows.wf1.events).toHaveLength(2);
  });

  it('mencatat status koneksi per workflow dan mengabaikan nilai yang sama', () => {
    const state = reduce(initialAppState, { type: 'workflow/connection', id: 'wf1', connection: 'connected' });
    expect(state.workflows.wf1.connection).toBe('connected');
    expect(appStateReducer(state, { type: 'workflow/connection', id: 'wf1', connection: 'connected' })).toBe(state);
    expect(appStateReducer(state, { type: 'workflow/connection', id: 'wf1', connection: 'reconnecting' }).workflows.wf1.connection).toBe('reconnecting');
  });

  it('data pantauan dibuang saat pengguna berganti', () => {
    const state = reduce(initialAppState, { type: 'workflow/loaded', id: 'wf1', workflow: wf(), events: [] });
    expect(appStateReducer(state, { type: 'session/changed', userId: 9, preferences: {} }).workflows).toEqual({});
  });
});
