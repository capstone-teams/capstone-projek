import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, useReducer, useMemo } from 'react';
import { createRoot } from 'react-dom/client';
import { AppStateContext } from '../src/context/appStateContext';
import WorkflowDetail from '../src/components/ai/WorkflowDetail';
import { FALLBACK_POLL_MS, LIVE_POLL_MS, useWorkflowMonitor } from '../src/hooks/useWorkflowMonitor';
import { SOCKET_STATUS } from '../src/services/monitoringSocket';
import * as workflowService from '../src/services/workflowService';
import { appStateReducer, initialAppState, workflowActions } from '../src/state/appState';

// Socket diganti kendali tes: tes memutuskan kapan koneksi tersambung, terputus, atau menerima frame.
const sockets = vi.hoisted(() => ({ subscriptions: [], calls: [] }));
vi.mock('../src/services/monitoringSocket', async (original) => ({
  ...(await original()),
  subscribeWorkflowEvents: (id, onEvent, onStatus) => {
    const subscription = { id, onEvent, onStatus, closed: false };
    sockets.subscriptions.push(subscription);
    sockets.calls.push('subscribe');
    onStatus?.('connecting');
    return () => { subscription.closed = true; };
  },
}));

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const wf = (overrides = {}) => ({
  id: 'wf1', status: 'RUNNING', stage: 'rps_processing', progress: { completed: 0, total: 2 }, rps_id: 'rps1',
  created_at: '2026-11-02T08:00:00Z', updated_at: '2026-11-02T08:00:00Z', moodle_course_id: null, ...overrides,
});
const ev = (event, stage, second, extra = {}) => ({
  event, workflow_id: 'wf1', stage, progress: { completed: 0, total: 2 }, message: `${event} ${stage}`,
  timestamp: `2026-11-02T08:00:${String(second).padStart(2, '0')}Z`, ...extra,
});

function Probe({ id = 'wf1' }) {
  const { workflow, events, connection, loading, error } = useWorkflowMonitor(id);
  return (
    <p data-testid="probe" data-connection={connection} data-loading={String(loading)} data-error={error ? 'ya' : 'tidak'}>
      {workflow ? `${workflow.status}/${workflow.stage}/${events.length}` : 'kosong'}
    </p>
  );
}

// Penyedia state aplikasi minimal (tanpa autentikasi) untuk memeriksa data yang dibagikan antarhalaman.
function SharedState({ children }) {
  const [state, dispatch] = useReducer(appStateReducer, initialAppState);
  const actions = useMemo(() => workflowActions(dispatch), []);
  return <AppStateContext.Provider value={{ ...state, ...actions }}>{children}</AppStateContext.Provider>;
}

describe('FE-10.2 pemantauan workflow real-time', () => {
  let container;
  let root;
  let current;
  let events;
  let getWorkflow;
  let getEvents;
  const probe = () => container.querySelector('[data-testid="probe"]');
  const mount = async (node) => {
    root = createRoot(container);
    await act(async () => root.render(node));
    await act(async () => { await vi.advanceTimersByTimeAsync(10); });
  };
  const connect = async (status = SOCKET_STATUS.CONNECTED) => {
    await act(async () => { sockets.subscriptions.at(-1).onStatus(status); await vi.advanceTimersByTimeAsync(10); });
  };
  const emit = async (event) => {
    await act(async () => { sockets.subscriptions.at(-1).onEvent(event); await vi.advanceTimersByTimeAsync(10); });
  };
  const tick = (ms) => act(async () => { await vi.advanceTimersByTimeAsync(ms); });

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: false });
    sockets.subscriptions = [];
    sockets.calls = [];
    current = wf();
    events = [ev('WORKFLOW_STARTED', null, 1)];
    getWorkflow = vi.spyOn(workflowService, 'getWorkflow').mockImplementation(async () => {
      sockets.calls.push('http');
      return current;
    });
    getEvents = vi.spyOn(workflowService, 'getWorkflowEvents').mockImplementation(async () => events);
    container = document.createElement('div');
    document.body.appendChild(container);
  });
  afterEach(() => {
    act(() => root?.unmount());
    root = null;
    container.remove();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('mengambil keadaan awal lewat HTTP lebih dulu, baru berlangganan event', async () => {
    await mount(<Probe />);
    expect(probe().textContent).toBe('RUNNING/rps_processing/1');
    expect(sockets.calls.indexOf('http')).toBeGreaterThanOrEqual(0);
    expect(sockets.calls.indexOf('http')).toBeLessThan(sockets.calls.indexOf('subscribe'));
    expect(sockets.subscriptions).toHaveLength(1);
    expect(sockets.subscriptions[0].id).toBe('wf1');
  });

  it('event yang diterima langsung memperbarui status dan daftar event tanpa permintaan HTTP baru', async () => {
    await mount(<Probe />);
    await connect();
    const requests = getWorkflow.mock.calls.length;
    await emit(ev('WORKFLOW_STAGE_COMPLETED', 'rps_processing', 5, { progress: { completed: 1, total: 2 } }));
    await emit(ev('WORKFLOW_STAGE_STARTED', 'rps_analysis', 6, { progress: { completed: 1, total: 2 } }));
    expect(probe().textContent).toBe('RUNNING/rps_analysis/3');
    expect(probe().dataset.connection).toBe('connected');
    expect(getWorkflow.mock.calls.length).toBe(requests);
  });

  it('event akhir memicu pengambilan status akhir dari server, lalu polling berhenti', async () => {
    await mount(<Probe />);
    await connect();
    current = wf({ status: 'FAILED', stage: null, updated_at: '2026-11-02T08:00:09Z' });
    events = [...events, ev('WORKFLOW_FAILED', 'rps_processing', 9)];
    const requests = getWorkflow.mock.calls.length;
    await emit(ev('WORKFLOW_FAILED', 'rps_processing', 9));
    expect(getWorkflow.mock.calls.length).toBe(requests + 1);
    expect(probe().textContent).toBe('FAILED/null/2');
    const after = getWorkflow.mock.calls.length;
    await tick(LIVE_POLL_MS * 3);
    expect(getWorkflow.mock.calls.length).toBe(after);
  });

  it('tersambung kembali menyinkronkan event yang terlewat selama koneksi terputus', async () => {
    await mount(<Probe />);
    await connect();
    await connect(SOCKET_STATUS.RECONNECTING);
    expect(probe().dataset.connection).toBe('reconnecting');
    // Selama terputus server menerbitkan event yang tidak sampai ke klien.
    current = wf({ stage: 'rps_analysis', updated_at: '2026-11-02T08:00:20Z' });
    events = [...events, ev('WORKFLOW_STAGE_STARTED', 'rps_analysis', 20)];
    await connect(SOCKET_STATUS.CONNECTED);
    expect(probe().textContent).toBe('RUNNING/rps_analysis/2');
    expect(probe().dataset.connection).toBe('connected');
  });

  it('polling cepat saat WebSocket terputus dan jarang saat tersambung', async () => {
    await mount(<Probe />);
    await connect(SOCKET_STATUS.RECONNECTING);
    let requests = getWorkflow.mock.calls.length;
    await tick(FALLBACK_POLL_MS * 3);
    expect(getWorkflow.mock.calls.length - requests).toBe(3);

    await connect(SOCKET_STATUS.CONNECTED);
    requests = getWorkflow.mock.calls.length; // termasuk sinkronisasi saat tersambung
    await tick(FALLBACK_POLL_MS * 3);
    expect(getWorkflow.mock.calls.length).toBe(requests);
    await tick(LIVE_POLL_MS);
    expect(getWorkflow.mock.calls.length).toBeGreaterThan(requests);
  });

  it('status tetap berubah lewat polling bila WebSocket tidak pernah tersambung (offline)', async () => {
    await mount(<Probe />);
    await connect(SOCKET_STATUS.OFFLINE);
    current = wf({ status: 'COMPLETED', stage: null, updated_at: '2026-11-02T08:00:30Z' });
    await tick(FALLBACK_POLL_MS + 10);
    expect(probe().textContent).toMatch(/^COMPLETED/);
  });

  it('kegagalan HTTP awal tampil sebagai error, lalu pulih sendiri lewat polling', async () => {
    getWorkflow.mockRejectedValueOnce(new Error('jaringan'));
    await mount(<Probe />);
    expect(probe().dataset.error).toBe('ya');
    expect(probe().dataset.loading).toBe('false');
    expect(sockets.subscriptions).toHaveLength(0); // belum ada keadaan awal, belum berlangganan
    await tick(FALLBACK_POLL_MS + 10);
    expect(probe().textContent).toBe('RUNNING/rps_processing/1');
    expect(probe().dataset.error).toBe('tidak');
    expect(sockets.subscriptions).toHaveLength(1);
  });

  it('langganan ditutup saat komponen dilepas', async () => {
    await mount(<Probe />);
    await act(async () => root.unmount());
    root = null;
    expect(sockets.subscriptions.every((subscription) => subscription.closed)).toBe(true);
  });

  it('data pantauan dibagikan lewat state aplikasi ke halaman lain', async () => {
    function Other() {
      const { workflow, events: shared } = useWorkflowMonitor('wf1');
      return <span data-testid="other">{workflow ? `${workflow.stage}/${shared.length}` : 'kosong'}</span>;
    }
    await mount(<SharedState><Probe /><Other /></SharedState>);
    await connect();
    await emit(ev('WORKFLOW_STAGE_STARTED', 'rps_analysis', 6));
    expect(probe().textContent).toBe('RUNNING/rps_analysis/2');
    expect(container.querySelector('[data-testid="other"]').textContent).toBe('rps_analysis/2');
  });

  it('WorkflowDetail menampilkan keterangan koneksi dan memberi tahu saat status berubah', async () => {
    const onChanged = vi.fn();
    await mount(<WorkflowDetail workflowId="wf1" rpsName="RPS Uji" onChanged={onChanged} />);
    await connect();
    const note = () => container.querySelector('[role="status"][data-connection]');
    expect(note().textContent).toBe('Status diperbarui otomatis.');
    expect(onChanged).not.toHaveBeenCalled();
    await emit(ev('WORKFLOW_STAGE_STARTED', 'rps_analysis', 6));
    await emit(ev('WORKFLOW_STAGE_PROGRESS', 'rps_analysis', 7));
    await emit(ev('WORKFLOW_STAGE_PROGRESS', 'rps_analysis', 8));
    expect(onChanged).not.toHaveBeenCalled(); // menunggu event beruntun selesai
    await tick(400);
    expect(onChanged).toHaveBeenCalledTimes(1);
    expect(container.querySelector('ol[aria-label="Riwayat event workflow"]').textContent).toContain('WORKFLOW_STAGE_STARTED rps_analysis');
    await connect(SOCKET_STATUS.RECONNECTING);
    expect(note().textContent).toMatch(/menyambungkan ulang/i);
    expect(container.textContent).not.toMatch(/WebSocket|socket/i);
    // Workflow berhenti: keterangan tidak diperlukan lagi.
    current = wf({ status: 'COMPLETED', stage: null, updated_at: '2026-11-02T08:00:40Z' });
    await emit(ev('WORKFLOW_COMPLETED', null, 40));
    expect(note()).toBeNull();
  });

  it('getWorkflowEvents ikut diambil bersama keadaan awal', async () => {
    await mount(<Probe />);
    expect(getEvents).toHaveBeenCalledWith('wf1');
  });
});
