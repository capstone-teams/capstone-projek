import { useCallback, useEffect, useMemo, useReducer, useRef } from 'react';
import { AppStateContext } from './appStateContext';
import { useAuth } from '../hooks/useAuth';
import { appStateReducer, createAppState, loadPreferences, savePreferences, toErrorEntry } from '../state/appState';

const BACKEND_ERROR_SOURCE = 'backend-auth';

function isAbort(error) {
  return error?.name === 'AbortError';
}

/**
 * State aplikasi bersama: preferensi UI (dipersist per user), notifikasi,
 * loading global dan error global. Harus berada di dalam <AuthProvider>.
 */
export function AppStateProvider({ children }) {
  const { user, backendError } = useAuth();
  const userId = user?.id ?? null;
  const [state, dispatch] = useReducer(appStateReducer, userId, createAppState);
  const nextId = useRef(0);

  // Pergantian user ditangani saat render supaya halaman tidak pernah melihat preferensi user lain.
  if (state.userId !== userId) {
    dispatch({ type: 'session/changed', userId, preferences: loadPreferences(userId) });
  }

  useEffect(() => {
    savePreferences(state.userId, state.preferences);
  }, [state.userId, state.preferences]);

  const setPreference = useCallback((key, value) => dispatch({ type: 'preference/set', key, value }), []);

  const notify = useCallback((message, { type = 'info' } = {}) => {
    const id = ++nextId.current;
    dispatch({ type: 'notification/push', notification: { id, message, type } });
    return id;
  }, []);
  const dismissNotification = useCallback((id) => dispatch({ type: 'notification/dismiss', id }), []);

  /** Mulai tugas loading global; kembalikan fungsi untuk menghentikannya (aman dipanggil berulang). */
  const startLoading = useCallback((label = 'Memproses…') => {
    const id = ++nextId.current;
    dispatch({ type: 'loading/start', task: { id, label } });
    let stopped = false;
    return () => {
      if (stopped) return;
      stopped = true;
      dispatch({ type: 'loading/stop', id });
    };
  }, []);

  const trackLoading = useCallback(async (task, label) => {
    const stop = startLoading(label);
    try {
      return await (typeof task === 'function' ? task() : task);
    } finally {
      stop();
    }
  }, [startLoading]);

  const reportError = useCallback((error, options) => {
    if (!error || isAbort(error)) return null;
    const id = ++nextId.current;
    dispatch({ type: 'error/report', error: toErrorEntry(id, error, options) });
    return id;
  }, []);
  const dismissError = useCallback((id) => dispatch({ type: 'error/dismiss', id }), []);
  const dismissErrorSource = useCallback((source) => dispatch({ type: 'error/dismiss', source }), []);
  const clearErrors = useCallback(() => dispatch({ type: 'error/clear' }), []);

  // Backend AI opsional: kegagalannya tidak memblokir Moodle, tetapi perlu terlihat oleh dosen.
  useEffect(() => {
    if (backendError) {
      reportError(backendError, { title: 'Generator AI belum dapat digunakan', source: BACKEND_ERROR_SOURCE });
    } else {
      dismissErrorSource(BACKEND_ERROR_SOURCE);
    }
  }, [backendError, reportError, dismissErrorSource]);

  const value = useMemo(
    () => ({
      ...state,
      isLoading: state.loading.length > 0,
      setPreference,
      notify,
      dismissNotification,
      startLoading,
      trackLoading,
      reportError,
      dismissError,
      dismissErrorSource,
      clearErrors,
    }),
    [state, setPreference, notify, dismissNotification, startLoading, trackLoading, reportError, dismissError, dismissErrorSource, clearErrors],
  );
  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}
