import { API_BASE_URL, USE_MOCK } from './config';
import { getToken } from './apiClient';
import { subscribeMockEvents, subscribeMockWorkflowEvents } from './mock/mockServer';

/** Buka WebSocket ke API backend dengan reconnect (backoff maks. 15 detik); kembalikan fungsi penutup. */
function openSocket(path, onEvent) {
  const { protocol, host } = window.location;
  const wsBase = API_BASE_URL.startsWith('http')
    ? API_BASE_URL.replace(/^http/, 'ws')
    : `${protocol === 'https:' ? 'wss' : 'ws'}://${host}${API_BASE_URL}`;
  // Browser tidak dapat menyetel header Authorization pada WebSocket: token dikirim lewat query (§17).
  const token = getToken();
  const url = `${wsBase}${path}${token ? `?token=${encodeURIComponent(token)}` : ''}`;

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

/**
 * Berlangganan event real-time satu course.
 * Panggil HTTP monitoring dulu untuk initial state, baru subscribe.
 * Mengembalikan fungsi unsubscribe.
 */
export function subscribeCourseEvents(courseId, onEvent) {
  if (USE_MOCK) return subscribeMockEvents(courseId, onEvent);
  return openSocket(`/ws/courses/${courseId}`, onEvent);
}

/**
 * Berlangganan event satu workflow (design-api §17: WS /ws/workflows/{workflow_id}).
 * Frame: { event: WORKFLOW_*, workflow_id, stage, progress, message, timestamp }.
 */
export function subscribeWorkflowEvents(workflowId, onEvent) {
  if (USE_MOCK) return subscribeMockWorkflowEvents(workflowId, onEvent);
  return openSocket(`/ws/workflows/${workflowId}`, onEvent);
}
