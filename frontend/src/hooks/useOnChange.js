import { useEffect, useRef } from 'react';
import { useLatest } from './useLatest';

/**
 * Panggil `callback(value)` setiap `value` berubah setelah nilai pertamanya diketahui. Nilai awal tidak memicu
 * callback, sehingga data yang baru saja dimuat tidak diambil ulang hanya karena halaman dibuka.
 * Nilai null/undefined dianggap "belum diketahui". `delayMs` menggabungkan perubahan beruntun.
 */
export function useOnChange(value, callback, delayMs = 0) {
  const previous = useRef(value);
  const latest = useLatest(callback);
  useEffect(() => {
    const before = previous.current;
    previous.current = value;
    if (value == null || before == null || before === value) return undefined;
    if (!delayMs) {
      latest.current(value);
      return undefined;
    }
    const timer = setTimeout(() => latest.current(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs, latest]);
}
