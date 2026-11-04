import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setToken } from '../src/services/apiClient';
import { SOCKET_STATUS, subscribeWorkflowEvents } from '../src/services/monitoringSocket';

// Menguji klien WebSocket sungguhan (bukan socket mock): konfigurasi tes memakai backend mock.
vi.mock('../src/services/config', async (original) => ({ ...(await original()), USE_MOCK: false, API_BASE_URL: '/api/v1' }));

class FakeSocket {
  static instances = [];
  constructor(url) {
    this.url = url;
    this.closed = false;
    FakeSocket.instances.push(this);
  }
  open() { this.onopen?.(); }
  receive(data) { this.onmessage?.({ data: typeof data === 'string' ? data : JSON.stringify(data) }); }
  drop(code = 1006) { this.onclose?.({ code }); }
  close() { this.closed = true; }
}
const last = () => FakeSocket.instances.at(-1);

describe('FE-10.2 klien WebSocket workflow', () => {
  let unsubscribers;
  const subscribe = (id, onEvent = () => {}, onStatus = () => {}) => {
    const stop = subscribeWorkflowEvents(id, onEvent, onStatus);
    unsubscribers.push(stop);
    return stop;
  };
  beforeEach(() => {
    vi.useFakeTimers();
    FakeSocket.instances = [];
    unsubscribers = [];
    vi.stubGlobal('WebSocket', FakeSocket);
    setToken('token-awal');
  });
  afterEach(() => {
    unsubscribers.forEach((stop) => stop());
    setToken(null);
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('terhubung ke /ws/workflows/{id} dengan token pada query, lalu meneruskan frame JSON', () => {
    const events = [];
    const statuses = [];
    subscribe('wf1', (event) => events.push(event), (status) => statuses.push(status));
    expect(last().url).toMatch(/^wss?:\/\/[^/]+\/api\/v1\/ws\/workflows\/wf1\?token=token-awal$/);
    expect(statuses).toEqual([SOCKET_STATUS.CONNECTING]);
    last().open();
    last().receive({ event: 'WORKFLOW_STARTED', workflow_id: 'wf1' });
    last().receive('bukan json');
    expect(statuses).toEqual([SOCKET_STATUS.CONNECTING, SOCKET_STATUS.CONNECTED]);
    expect(events).toEqual([{ event: 'WORKFLOW_STARTED', workflow_id: 'wf1' }]);
  });

  it('tersambung kembali otomatis setelah terputus, dengan jeda yang makin panjang dan token terbaru', () => {
    const statuses = [];
    subscribe('wf1', () => {}, (status) => statuses.push(status));
    last().open();
    last().drop();
    expect(statuses.at(-1)).toBe(SOCKET_STATUS.RECONNECTING);
    expect(FakeSocket.instances).toHaveLength(1);

    setToken('token-baru');
    vi.advanceTimersByTime(999);
    expect(FakeSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(FakeSocket.instances).toHaveLength(2);
    expect(last().url).toContain('token=token-baru');

    last().drop(); // gagal sebelum sempat terbuka: jeda berikutnya 2 detik
    vi.advanceTimersByTime(1999);
    expect(FakeSocket.instances).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(FakeSocket.instances).toHaveLength(3);

    last().open();
    expect(statuses.at(-1)).toBe(SOCKET_STATUS.CONNECTED);
    last().drop(); // berhasil tersambung lagi: jeda kembali 1 detik
    vi.advanceTimersByTime(1000);
    expect(FakeSocket.instances).toHaveLength(4);
  });

  it('jeda tidak melebihi 15 detik', () => {
    subscribe('wf1');
    for (let i = 0; i < 8; i += 1) {
      last().drop();
      vi.advanceTimersByTime(15000);
    }
    const before = FakeSocket.instances.length;
    last().drop();
    vi.advanceTimersByTime(14999);
    expect(FakeSocket.instances).toHaveLength(before);
    vi.advanceTimersByTime(1);
    expect(FakeSocket.instances).toHaveLength(before + 1);
  });

  it('tersambung segera saat jaringan kembali tanpa menunggu sisa jeda', () => {
    subscribe('wf1');
    last().open();
    last().drop();
    window.dispatchEvent(new Event('online'));
    expect(FakeSocket.instances).toHaveLength(2);
    vi.advanceTimersByTime(30000); // jeda lama tidak membuat sambungan ganda
    expect(FakeSocket.instances).toHaveLength(2);
  });

  it('ditolak saat handshake (4401/4403/4404) berarti offline dan tidak dicoba lagi', () => {
    const statuses = [];
    subscribe('wf1', () => {}, (status) => statuses.push(status));
    last().drop(4401);
    expect(statuses.at(-1)).toBe(SOCKET_STATUS.OFFLINE);
    vi.advanceTimersByTime(60000);
    expect(FakeSocket.instances).toHaveLength(1);
  });

  it('tanpa token tidak membuka koneksi dan dilaporkan offline', () => {
    setToken(null);
    const statuses = [];
    subscribe('wf1', () => {}, (status) => statuses.push(status));
    expect(FakeSocket.instances).toHaveLength(0);
    expect(statuses).toEqual([SOCKET_STATUS.OFFLINE]);
  });

  it('satu koneksi dipakai bersama; ditutup setelah pelanggan terakhir berhenti', () => {
    const first = [];
    const second = [];
    const stopFirst = subscribe('wf1', (event) => first.push(event));
    last().open();
    const lateStatuses = [];
    const stopSecond = subscribe('wf1', (event) => second.push(event), (status) => lateStatuses.push(status));
    expect(FakeSocket.instances).toHaveLength(1);
    expect(lateStatuses).toEqual([SOCKET_STATUS.CONNECTED]); // pelanggan baru langsung tahu status terkini
    last().receive({ event: 'WORKFLOW_STAGE_STARTED' });
    expect(first).toHaveLength(1);
    expect(second).toHaveLength(1);
    const socket = last();
    stopFirst();
    expect(socket.closed).toBe(false);
    stopSecond();
    expect(socket.closed).toBe(true);
    // Setelah ditutup, sambungan lama yang terlambat menutup tidak memicu reconnect.
    socket.drop();
    vi.advanceTimersByTime(30000);
    expect(FakeSocket.instances).toHaveLength(1);
  });

  it('workflow berbeda memakai koneksi berbeda', () => {
    subscribe('wf1');
    subscribe('wf2');
    expect(FakeSocket.instances.map((socket) => socket.url.match(/workflows\/(\w+)/)[1])).toEqual(['wf1', 'wf2']);
  });
});
