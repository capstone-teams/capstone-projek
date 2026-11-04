import { useCallback, useEffect, useState } from 'react';
import { getWorkflow, getWorkflowEvents, listWorkflows } from '../services/workflowService';
import { getRps } from '../services/rpsService';
import { subscribeWorkflowEvents } from '../services/monitoringSocket';
import { useLatest } from './useLatest';

/**
 * Hook untuk mengelola data alur kerja (Workflow) aktif:
 * - Menyelesaikan active workflowId dari relasi course atau RPS
 * - Mengambil detail workflow dan riwayat event (HTTP)
 * - Berlangganan event real-time melalui WebSocket
 */
export function useWorkflow(course, explicitWorkflowId = null) {
  const [workflowId, setWorkflowId] = useState(explicitWorkflowId || course?.workflow_id || null);
  const [workflow, setWorkflow] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 1. Selesaikan workflow_id jika belum tersedia secara langsung
  useEffect(() => {
    let active = true;

    async function resolveId() {
      if (explicitWorkflowId) {
        setWorkflowId(explicitWorkflowId);
        return;
      }
      if (course?.workflow_id) {
        setWorkflowId(course.workflow_id);
        return;
      }
      if (course?.rps_id) {
        try {
          const rps = await getRps(course.rps_id);
          if (active && rps?.workflow_id) {
            setWorkflowId(rps.workflow_id);
            return;
          }
        } catch {
          // Abaikan jika gagal baca RPS
        }
      }
      try {
        const wfList = await listWorkflows();
        if (!active) return;
        const matching = (wfList?.items ?? []).find((w) => w.rps_id && w.rps_id === course?.rps_id);
        if (matching?.id) {
          setWorkflowId(matching.id);
        } else if (wfList?.items?.length) {
          setWorkflowId(wfList.items[0].id);
        }
      } catch {
        // Abaikan jika list workflow gagal
      }
    }

    resolveId();
    return () => {
      active = false;
    };
  }, [course?.workflow_id, course?.rps_id, explicitWorkflowId]);

  // 2. Fetch detail workflow dan event awal via HTTP
  const loadData = useCallback(async () => {
    if (!workflowId) return;
    setLoading(true);
    setError(null);
    try {
      const [detailRes, eventsRes] = await Promise.all([
        getWorkflow(workflowId).catch(() => null),
        getWorkflowEvents(workflowId).catch(() => ({ items: [] })),
      ]);
      setWorkflow(detailRes);
      setEvents(eventsRes?.items ?? []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    let active = true;

    async function fetchInitial() {
      if (!workflowId) return;
      try {
        const [detailRes, eventsRes] = await Promise.all([
          getWorkflow(workflowId).catch(() => null),
          getWorkflowEvents(workflowId).catch(() => ({ items: [] })),
        ]);
        if (!active) return;
        setWorkflow(detailRes);
        setEvents(eventsRes?.items ?? []);
      } catch (err) {
        if (!active) return;
        setError(err);
      }
    }

    fetchInitial();
    return () => {
      active = false;
    };
  }, [workflowId]);

  // 3. Berlangganan event real-time lewat WebSocket
  const onNewEvent = useCallback((newEvent) => {
    setEvents((prev) => {
      const exists = prev.some(
        (e) => e.timestamp === newEvent.timestamp && e.event === newEvent.event,
      );
      if (exists) return prev;
      return [...prev.slice(-199), newEvent];
    });

    if (newEvent.stage || newEvent.progress) {
      setWorkflow((prev) => (prev ? {
        ...prev,
        stage: newEvent.stage ?? prev.stage,
        progress: newEvent.progress ?? prev.progress,
        status: newEvent.event === 'WORKFLOW_COMPLETED'
          ? 'COMPLETED'
          : newEvent.event === 'WORKFLOW_FAILED'
            ? 'FAILED'
            : prev.status,
      } : null));
    }
  }, []);

  const latestHandler = useLatest(onNewEvent);

  useEffect(() => {
    if (!workflowId) return undefined;
    return subscribeWorkflowEvents(workflowId, (ev) => latestHandler.current(ev));
  }, [workflowId, latestHandler]);

  return {
    workflowId,
    workflow,
    events,
    loading,
    error,
    reload: loadData,
  };
}
