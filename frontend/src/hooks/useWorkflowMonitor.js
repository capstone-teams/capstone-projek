import { useCallback, useEffect, useRef, useState } from 'react';
import { SOCKET_STATUS } from '../services/monitoringSocket';
import { getWorkflow, getWorkflowEvents } from '../services/workflowService';
import { isFinalWorkflowEvent, isWorkflowFinished } from '../utils/workflowStatus';
import { usePolling } from './usePolling';
import { useWorkflowSubscription } from './useWorkflowEvents';
import { useWorkflowStore } from './useWorkflowStore';

// Saat WebSocket tersambung, polling hanya jaring pengaman bagi event yang mungkin terlewat; saat terputus,
// polling menjadi sumber pembaruan sampai koneksi pulih.
export const LIVE_POLL_MS = 15000;
export const FALLBACK_POLL_MS = 4000;

/**
 * Memantau satu workflow secara real-time (FE-10.2):
 * 1. keadaan awal diambil lewat HTTP (GET /workflows/{id} dan /events);
 * 2. baru berlangganan ke WS /ws/workflows/{id}; event yang tiba langsung diterapkan ke status dan daftar event;
 * 3. tiap koneksi tersambung (juga setelah terputus) dan setelah event akhir, keadaan disinkronkan ulang lewat
 *    HTTP karena server hanya mengirim event baru;
 * 4. selama workflow belum berhenti polling berjalan, cepat bila WebSocket terputus dan jarang bila tersambung.
 * Hasilnya disimpan di state aplikasi, sehingga halaman lain memakai data yang sama.
 */
export function useWorkflowMonitor(workflowId) {
  const store = useWorkflowStore();
  const entry = workflowId ? store.workflows[workflowId] : null;
  // Kegagalan terakhir beserta workflow-nya, agar galat satu workflow tidak tampil di workflow lain.
  const [failure, setFailure] = useState(null);
  const error = failure && failure.id === workflowId ? failure.error : null;
  const calls = useRef(0);
  const { loadWorkflow } = store;

  const sync = useCallback(async () => {
    if (!workflowId) return null;
    const call = ++calls.current;
    try {
      const [workflow, events] = await Promise.all([getWorkflow(workflowId), getWorkflowEvents(workflowId)]);
      // Jawaban yang sudah disusul permintaan lebih baru dibuang agar tidak menimpa keadaan yang lebih segar.
      if (call !== calls.current) return null;
      loadWorkflow(workflowId, workflow, events);
      setFailure(null);
      return workflow;
    } catch (e) {
      if (call === calls.current) setFailure({ id: workflowId, error: e });
      return null;
    }
  }, [workflowId, loadWorkflow]);

  useEffect(() => {
    // setState di sync terjadi setelah await, bukan sinkron di dalam effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    sync();
    return () => {
      calls.current += 1;
    };
  }, [sync]);

  const workflow = entry?.workflow ?? null;
  const connected = !!workflow && entry.connection === SOCKET_STATUS.CONNECTED;

  // Berlangganan baru setelah keadaan awal ada.
  useWorkflowSubscription(
    store,
    workflow ? [workflowId] : [],
    (event) => {
      if (isFinalWorkflowEvent(event)) sync();
    },
    (status) => {
      if (status === SOCKET_STATUS.CONNECTED) sync();
    },
  );
  usePolling(sync, connected ? LIVE_POLL_MS : FALLBACK_POLL_MS, !!workflowId && !isWorkflowFinished(workflow));

  return {
    workflow,
    events: entry?.events ?? [],
    // 'connected' | 'connecting' | 'reconnecting' | 'offline' (lihat SOCKET_STATUS).
    connection: workflow ? entry.connection : SOCKET_STATUS.CONNECTING,
    loading: !!workflowId && !workflow && !error,
    error,
    reload: sync,
  };
}
