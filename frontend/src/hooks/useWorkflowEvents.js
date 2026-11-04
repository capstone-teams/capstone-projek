import { useEffect } from 'react';
import { subscribeWorkflowEvents } from '../services/monitoringSocket';
import { useLatest } from './useLatest';

/**
 * Berlangganan event beberapa workflow (design-api §17); `onEvent` dipanggil untuk tiap frame.
 * Langganan dibuka ulang hanya bila daftar workflow berubah.
 */
export function useWorkflowEvents(workflowIds, onEvent) {
  const ref = useLatest(onEvent);
  const key = [...new Set(workflowIds.filter(Boolean))].sort().join(',');

  useEffect(() => {
    if (!key) return undefined;
    const unsubscribers = key.split(',').map((id) => subscribeWorkflowEvents(id, (event) => ref.current(event)));
    return () => unsubscribers.forEach((unsubscribe) => unsubscribe());
  }, [ref, key]);
}
