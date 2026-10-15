import { useCallback, useContext, useState } from 'react';
import { AppStateContext } from '../context/appStateContext';

/** Seluruh state aplikasi bersama dari AppStateProvider. */
export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState harus dipakai di dalam <AppStateProvider>.');
  return ctx;
}

/**
 * Preferensi UI yang dipersist per user. Tanpa provider (mis. pada tes komponen)
 * nilainya hanya disimpan sebagai state lokal komponen.
 */
export function usePreference(key, fallback) {
  const ctx = useContext(AppStateContext);
  const [local, setLocal] = useState(fallback);
  const setPreference = ctx?.setPreference;
  const value = ctx ? (ctx.preferences[key] ?? fallback) : local;
  const setValue = useCallback(
    (next) => (setPreference ? setPreference(key, next) : setLocal(next)),
    [setPreference, key],
  );
  return [value, setValue];
}
