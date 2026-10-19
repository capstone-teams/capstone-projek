import { API_BASE_URL, USE_MOCK } from './config';
import { getToken } from './apiClient';
import { subscribeMockEvents } from './mock/mockServer';

/**
 * Berlangganan event real-time satu course (design-api.md §17).
 * Panggil HTTP monitoring dulu untuk initial state, baru subscribe.
 * Mengembalikan fungsi unsubscribe.
 */
export function subscribeCourseEvents(courseId, onEvent) {
  if (USE_MOCK) return subscribeMockEvents(courseId, onEvent);

  const { protocol, host } = window.location;
  const wsBase = API_BASE_URL.startsWith('http')
    ? API_BASE_URL.replace(/^http/, 'ws')
    : `${protocol === 'https:' ? 'wss' : 'ws'}://${host}${API_BASE_URL}`;
  // Mekanisme auth WebSocket belum diputuskan (design-api.md §28 no. 8); sementara via query.
  const token = getToken();
  const url = `${wsBase}/ws/courses/${courseId}${token ? `?token=${encodeURIComponent(token)}` : ''}`;

  let socket;
  let closed = false;
  let retry = 0;
  let timer;

  const connect = () => {
    socket = new WebSocket(url);
    socket.onopen = () => {
      retry = 0;
    };
    socket.onmessage = (msg) => {
      try {
        onEvent(JSON.parse(msg.data));
      } catch {
        // Abaikan pesan yang bukan JSON.
      }
    };
    socket.onclose = () => {
      if (closed) return;
      // Reconnect dengan backoff sederhana, maksimal 15 detik.
      timer = setTimeout(connect, Math.min(1000 * 2 ** retry++, 15000));
    };
  };
  connect();

  return () => {
    closed = true;
    clearTimeout(timer);
    socket?.close();
  };
}
