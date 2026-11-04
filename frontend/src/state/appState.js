import { PREFERENCES_STORAGE_KEY } from '../services/config';
import { readJson, writeJson } from '../utils/storage';
import { applyWorkflowEvent, eventKey, mergeEvents } from '../utils/workflowStatus';

// State aplikasi lintas halaman. Reducer dibuat murni (tanpa side effect) supaya mudah diuji;
// id dan penyimpanan diurus oleh AppStateProvider.
//
// - preferences   : UI state yang dipersist per user (mis. filter "Kursus saya").
// - notifications : toast singkat.
// - loading       : aksi yang sedang berjalan dan perlu terlihat di seluruh aplikasi.
// - errors        : error yang tidak dimiliki satu halaman (mis. backend AI tidak tersedia).
// - workflows     : pantauan workflow per id (FE-10.2): snapshot, event, dan status koneksi real-time,
//                   dipakai bersama oleh halaman status workflow, daftar RPS (FE-08.2), dan dashboard (FE-11.1).

export const MAX_NOTIFICATIONS = 3;

export const initialAppState = {
  userId: null,
  preferences: {},
  notifications: [],
  loading: [],
  errors: [],
  workflows: {},
};

const emptyMonitor = { workflow: null, events: [], connection: 'connecting' };

/** Pembuat action untuk slice `workflows`; dipakai AppStateProvider dan hook saat tanpa provider. */
export const workflowActions = (dispatch) => ({
  loadWorkflow: (id, workflow, events) => dispatch({ type: 'workflow/loaded', id, workflow, events }),
  receiveWorkflowEvent: (id, event) => dispatch({ type: 'workflow/event', id, event }),
  setWorkflowConnection: (id, connection) => dispatch({ type: 'workflow/connection', id, connection }),
});

export function createAppState(userId = null) {
  return { ...initialAppState, userId, preferences: loadPreferences(userId) };
}

// Penghapusan yang tidak mengubah apa pun mengembalikan state yang sama (tanpa render ulang).
function withList(state, key, next) {
  return next.length === state[key].length ? state : { ...state, [key]: next };
}

export function appStateReducer(state, action) {
  switch (action.type) {
    case 'session/changed':
      // Ganti user/logout: state transient dibuang, preferensi diambil milik user baru.
      return { ...initialAppState, userId: action.userId, preferences: action.preferences ?? {} };
    case 'preference/set':
      if (state.preferences[action.key] === action.value) return state;
      return { ...state, preferences: { ...state.preferences, [action.key]: action.value } };
    case 'notification/push':
      return { ...state, notifications: [...state.notifications, action.notification].slice(-MAX_NOTIFICATIONS) };
    case 'notification/dismiss':
      return withList(state, 'notifications', state.notifications.filter((n) => n.id !== action.id));
    case 'loading/start':
      return { ...state, loading: [...state.loading, action.task] };
    case 'loading/stop':
      return withList(state, 'loading', state.loading.filter((t) => t.id !== action.id));
    case 'error/report': {
      // Satu sumber hanya punya satu error aktif: laporan baru menggantikan yang lama.
      const { source } = action.error;
      const rest = source ? state.errors.filter((e) => e.source !== source) : state.errors;
      return { ...state, errors: [...rest, action.error] };
    }
    case 'error/dismiss':
      return withList(
        state,
        'errors',
        state.errors.filter((e) => (action.id != null ? e.id !== action.id : e.source !== action.source)),
      );
    case 'error/clear':
      return withList(state, 'errors', []);
    case 'workflow/loaded': {
      // Snapshot HTTP: event yang tiba lewat WebSocket sebelum jawaban datang diterapkan kembali di atasnya.
      const current = state.workflows[action.id] ?? emptyMonitor;
      const events = mergeEvents(current.events, action.events ?? []);
      const workflow = events.reduce(applyWorkflowEvent, action.workflow);
      return { ...state, workflows: { ...state.workflows, [action.id]: { ...current, workflow, events } } };
    }
    case 'workflow/event': {
      const current = state.workflows[action.id] ?? emptyMonitor;
      const key = eventKey(action.event);
      if (current.events.some((event) => eventKey(event) === key)) return state;
      const next = { ...current, events: mergeEvents(current.events, [action.event]), workflow: applyWorkflowEvent(current.workflow, action.event) };
      return { ...state, workflows: { ...state.workflows, [action.id]: next } };
    }
    case 'workflow/connection': {
      const current = state.workflows[action.id] ?? emptyMonitor;
      if (state.workflows[action.id] && current.connection === action.connection) return state;
      return { ...state, workflows: { ...state.workflows, [action.id]: { ...current, connection: action.connection } } };
    }
    default:
      return state;
  }
}

export function toErrorEntry(id, error, { title, source } = {}) {
  const message = (typeof error === 'string' ? error : error?.message) || 'Terjadi kesalahan yang tidak terduga.';
  return { id, title: title ?? null, message, code: error?.code ?? null, source: source ?? null };
}

export function preferencesKey(userId) {
  return `${PREFERENCES_STORAGE_KEY}.${userId}`;
}

export function loadPreferences(userId) {
  if (userId == null) return {};
  const stored = readJson(preferencesKey(userId));
  return stored && typeof stored === 'object' && !Array.isArray(stored) ? stored : {};
}

export function savePreferences(userId, preferences) {
  if (userId == null) return false;
  return writeJson(preferencesKey(userId), preferences);
}
