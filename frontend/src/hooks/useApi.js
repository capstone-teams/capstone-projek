import { useCallback, useEffect, useRef, useState } from 'react';
import { useLatest } from './useLatest';

/**
 * Memuat data dari service saat komponen mount dan ketika `deps` berubah.
 * Mengembalikan { data, error, loading, reload, setData }.
 */
export function useApi(fetcher, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true, dependencies: null });
  const fetcherRef = useLatest(fetcher);
  const depsRef = useLatest(deps);
  const callId = useRef(0);

  const reload = useCallback(async ({ silent = false } = {}) => {
    const id = ++callId.current;
    const dependencies = depsRef.current;
    if (!silent) setState({ data: null, loading: true, error: null, dependencies });
    try {
      const data = await fetcherRef.current();
      if (id === callId.current) setState({ data, error: null, loading: false, dependencies });
      return data;
    } catch (error) {
      if (id === callId.current) setState((s) => ({ ...s, error, loading: false, dependencies }));
      return null;
    }
  }, [fetcherRef, depsRef]);

  useEffect(() => {
    reload();
    // This is a request generation counter, not a DOM ref; invalidate the latest request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    return () => { callId.current++; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  const setData = useCallback((updater) => {
    setState((s) => ({ ...s, data: typeof updater === 'function' ? updater(s.data) : updater }));
  }, []);

  const current = state.dependencies?.length === deps.length
    && deps.every((value, index) => Object.is(value, state.dependencies[index]));
  return { ...(current ? state : { data: null, error: null, loading: true }), reload, setData };
}

/**
 * Membungkus aksi (POST/PUT) dengan state pending & error.
 * run() melempar ulang error supaya pemanggil bisa bereaksi bila perlu.
 */
export function useAction(action) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const actionRef = useLatest(action);

  const run = useCallback(async (...args) => {
    setPending(true);
    setError(null);
    try {
      return await actionRef.current(...args);
    } catch (e) {
      setError(e);
      throw e;
    } finally {
      setPending(false);
    }
  }, [actionRef]);

  return { run, pending, error, clearError: () => setError(null) };
}
