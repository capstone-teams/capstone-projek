import { useEffect } from 'react';
import { subscribeWorkflowEvents } from '../services/monitoringSocket';
import { useLatest } from './useLatest';
import { useWorkflowStore } from './useWorkflowStore';

/**
 * Berlangganan event beberapa workflow ke `store` (useWorkflowStore): tiap frame dan perubahan status
 * koneksi dicatat di state aplikasi, lalu diteruskan ke `onEvent(event)` dan `onStatus(status, id)`.
 * Langganan dibuka ulang hanya bila daftar workflow berubah.
 */
export function useWorkflowSubscription(store, workflowIds, onEvent, onStatus) {
  const eventRef = useLatest(onEvent);
  const statusRef = useLatest(onStatus);
  const { receiveWorkflowEvent, setWorkflowConnection } = store;
  const key = [...new Set(workflowIds.filter(Boolean))].sort().join(',');

  useEffect(() => {
    if (!key) return undefined;
    const unsubscribers = key.split(',').map((id) => subscribeWorkflowEvents(
      id,
      (event) => {
        receiveWorkflowEvent(id, event);
        eventRef.current?.(event);
      },
      (status) => {
        setWorkflowConnection(id, status);
        statusRef.current?.(status, id);
      },
    ));
    return () => unsubscribers.forEach((unsubscribe) => unsubscribe());
  }, [eventRef, statusRef, receiveWorkflowEvent, setWorkflowConnection, key]);
}

/** Berlangganan event beberapa workflow (design-api §17); `onEvent` dipanggil untuk tiap frame. */
export function useWorkflowEvents(workflowIds, onEvent, onStatus) {
  useWorkflowSubscription(useWorkflowStore(), workflowIds, onEvent, onStatus);
}
