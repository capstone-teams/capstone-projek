import { useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AppStateContext } from '../context/appStateContext';
import { useLatest } from './useLatest';

/**
 * Memuat data dari service saat komponen mount dan ketika `deps` berubah.
 * Mengembalikan { data, error, loading, reload, setData }.
 */
export function useApi(fetcher, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const fetcherRef = useLatest(fetcher);
  const callId = useRef(0);

  const reload = useCallback(async ({ silent = false } = {}) => {
    const id = ++callId.current;
    if (!silent) setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await fetcherRef.current();
      if (id === callId.current) setState({ data, error: null, loading: false });
      return data;
    } catch (error) {
      if (id === callId.current) setState((s) => ({ ...s, error, loading: false }));
      return null;
    }
  }, [fetcherRef]);

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  const setData = useCallback((updater) => {
    setState((s) => ({ ...s, data: typeof updater === 'function' ? updater(s.data) : updater }));
  }, []);

  return { ...state, reload, setData };
}

/**
 * Membungkus aksi (POST/PUT) dengan state pending & error.
 * run() melempar ulang error supaya pemanggil bisa bereaksi bila perlu.
 * `loadingLabel` juga mendaftarkan aksi ke loading global AppStateProvider (bila ada).
 */
export function useAction(action, { loadingLabel } = {}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const actionRef = useLatest(action);
  const startLoading = useContext(AppStateContext)?.startLoading;

  const run = useCallback(async (...args) => {
    setPending(true);
    setError(null);
    const stopLoading = loadingLabel && startLoading ? startLoading(loadingLabel) : null;
    try {
      return await actionRef.current(...args);
    } catch (e) {
      setError(e);
      throw e;
    } finally {
      stopLoading?.();
      setPending(false);
    }
  }, [actionRef, loadingLabel, startLoading]);

  return { run, pending, error, clearError: () => setError(null) };
}
