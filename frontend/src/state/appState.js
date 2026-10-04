import { PREFERENCES_STORAGE_KEY } from '../services/config';
import { readJson, writeJson } from '../utils/storage';

// State aplikasi lintas halaman. Reducer dibuat murni (tanpa side effect) supaya mudah diuji;
// id dan penyimpanan diurus oleh AppStateProvider.
//
// - preferences   : UI state yang dipersist per user (mis. filter "Kursus saya").
// - notifications : toast singkat.
// - loading       : aksi yang sedang berjalan dan perlu terlihat di seluruh aplikasi.
// - errors        : error yang tidak dimiliki satu halaman (mis. backend AI tidak tersedia).

export const MAX_NOTIFICATIONS = 3;

export const initialAppState = {
  userId: null,
  preferences: {},
  notifications: [],
  loading: [],
  errors: [],
};

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
