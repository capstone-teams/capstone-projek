import { API_BASE_URL, USE_MOCK } from './config';
import { getToken } from './apiClient';
import { subscribeMockEvents, subscribeMockWorkflowEvents } from './mock/mockServer';

/** Status koneksi real-time yang dilaporkan ke pelanggan. */
export const SOCKET_STATUS = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  // Tidak dapat tersambung (token ditolak, workflow tidak ditemukan, atau belum login): pemanggil memakai polling.
  OFFLINE: 'offline',
};

// 4401/4403/4404: ditolak saat handshake; mencoba lagi tidak akan berhasil.
const REJECTED_CODES = [4401, 4403, 4404];
const MAX_BACKOFF_MS = 15000;

function socketUrl(path, token) {
  const { protocol, host } = window.location;
  const wsBase = API_BASE_URL.startsWith('http')
    ? API_BASE_URL.replace(/^http/, 'ws').replace(/\/+$/, '')
    : `${protocol === 'https:' ? 'wss' : 'ws'}://${host}${API_BASE_URL.replace(/\/+$/, '')}`;
  // Browser tidak dapat menyetel header Authorization pada WebSocket: token dikirim lewat query (§17).
  return `${wsBase}${path}?token=${encodeURIComponent(token)}`;
}

/**
 * Satu koneksi WebSocket ke `path` dengan reconnect otomatis (backoff maks. 15 detik). Token dibaca ulang
 * pada setiap percobaan, dan percobaan diulang segera saat jaringan atau tab kembali aktif.
 */
function createChannel(path) {
  const channel = { status: SOCKET_STATUS.CONNECTING, listeners: new Set(), watchers: new Set(), close: () => {} };
  let socket;
  let closed = false;
  let retry = 0;
  let timer;

  const setStatus = (status) => {
    if (channel.status === status) return;
    channel.status = status;
    [...channel.watchers].forEach((watcher) => watcher(status));
  };

  const connect = () => {
    clearTimeout(timer);
    const token = getToken();
    if (!token) {
      setStatus(SOCKET_STATUS.OFFLINE);
      return;
    }
    const current = new WebSocket(socketUrl(path, token));
    socket = current;
    current.onopen = () => {
      if (socket !== current) return;
      retry = 0;
      setStatus(SOCKET_STATUS.CONNECTED);
    };
    current.onmessage = (msg) => {
      if (socket !== current) return;
      let frame;
      try {
        frame = JSON.parse(msg.data);
      } catch {
        return; // Abaikan pesan yang bukan JSON.
      }
      [...channel.listeners].forEach((listener) => listener(frame));
    };
    current.onclose = (event) => {
      if (closed || socket !== current) return;
      if (REJECTED_CODES.includes(event.code)) {
        setStatus(SOCKET_STATUS.OFFLINE);
        return;
      }
      setStatus(SOCKET_STATUS.RECONNECTING);
      timer = setTimeout(connect, Math.min(1000 * 2 ** retry++, MAX_BACKOFF_MS));
    };
  };

  // Jaringan pulih atau tab dibuka lagi: tidak perlu menunggu sisa backoff.
  const retryNow = () => {
    if (closed || channel.status !== SOCKET_STATUS.RECONNECTING) return;
    retry = 0;
    connect();
  };
  const onVisible = () => document.visibilityState === 'visible' && retryNow();
  window.addEventListener('online', retryNow);
  document.addEventListener('visibilitychange', onVisible);

  channel.close = () => {
    closed = true;
    clearTimeout(timer);
    window.removeEventListener('online', retryNow);
    document.removeEventListener('visibilitychange', onVisible);
    socket?.close();
  };
  connect();
  return channel;
}

// Satu koneksi per path, dipakai bersama semua pelanggan; ditutup saat pelanggan terakhir berhenti.
const channels = new Map();

function subscribeChannel(path, onEvent, onStatus) {
  let channel = channels.get(path);
  if (!channel) {
    channel = createChannel(path);
    channels.set(path, channel);
  }
  channel.listeners.add(onEvent);
  if (onStatus) {
    channel.watchers.add(onStatus);
    onStatus(channel.status);
  }
  return () => {
    channel.listeners.delete(onEvent);
    if (onStatus) channel.watchers.delete(onStatus);
    if (!channel.listeners.size && channels.get(path) === channel) {
      channels.delete(path);
      channel.close();
    }
  };
}

/**
 * Berlangganan event real-time satu course.
 * Panggil HTTP monitoring dulu untuk initial state, baru subscribe.
 * Mengembalikan fungsi unsubscribe.
 */
export function subscribeCourseEvents(courseId, onEvent, onStatus) {
  if (USE_MOCK) {
    onStatus?.(SOCKET_STATUS.CONNECTED);
    return subscribeMockEvents(courseId, onEvent);
  }
  return subscribeChannel(`/ws/courses/${courseId}`, onEvent, onStatus);
}

/**
 * Berlangganan event satu workflow (design-api §17: WS /ws/workflows/{workflow_id}).
 * Frame: { event: WORKFLOW_*, workflow_id, stage, progress, message, timestamp }. Server hanya mengirim
 * event baru setelah tersambung, jadi pemanggil mengambil keadaan awal lewat HTTP dan menyinkronkannya
 * lagi tiap `onStatus` melaporkan CONNECTED. `onStatus(status)` menerima nilai SOCKET_STATUS.
 */
export function subscribeWorkflowEvents(workflowId, onEvent, onStatus) {
  if (USE_MOCK) {
    onStatus?.(SOCKET_STATUS.CONNECTED);
    return subscribeMockWorkflowEvents(workflowId, onEvent);
  }
  return subscribeChannel(`/ws/workflows/${workflowId}`, onEvent, onStatus);
}
