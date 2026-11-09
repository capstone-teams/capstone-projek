import { API_BASE_URL } from './config';
import { getToken } from './apiClient';

/** Status koneksi real-time yang dilaporkan ke pelanggan. */
export const SOCKET_STATUS = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  OFFLINE: 'offline',
};

const REJECTED_CODES = [4401, 4403, 4404];
const MAX_BACKOFF_MS = 15000;

function socketUrl(path, token) {
  const { protocol, host } = window.location;
  const wsBase = API_BASE_URL.startsWith('http')
    ? API_BASE_URL.replace(/^http/, 'ws').replace(/\/+$/, '')
    : `${protocol === 'https:' ? 'wss' : 'ws'}://${host}${API_BASE_URL.replace(/\/+$/, '')}`;
  return `${wsBase}${path}?token=${encodeURIComponent(token)}`;
}

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
        return;
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

export function subscribeCourseEvents(courseId, onEvent, onStatus) {
  return subscribeChannel(`/ws/courses/${courseId}`, onEvent, onStatus);
}

export function subscribeWorkflowEvents(workflowId, onEvent, onStatus) {
  return subscribeChannel(`/ws/workflows/${workflowId}`, onEvent, onStatus);
}
