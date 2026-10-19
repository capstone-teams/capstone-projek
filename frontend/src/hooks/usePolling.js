import { useEffect } from 'react';
import { useLatest } from './useLatest';

/** Memanggil `callback` setiap `intervalMs` selama `active` bernilai true. */
export function usePolling(callback, intervalMs, active) {
  const ref = useLatest(callback);

  useEffect(() => {
    if (!active) return undefined;
    const id = setInterval(() => ref.current(), intervalMs);
    return () => clearInterval(id);
  }, [ref, intervalMs, active]);
}
