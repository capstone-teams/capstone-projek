import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useApi } from './useApi';
import { usePolling } from './usePolling';
import { useWorkflowEvents } from './useWorkflowEvents';
import { getRps, listRps, processRps, reanalyzeRps } from '../services/rpsService';
import { RPS_STATUS, isRpsInProgress } from '../utils/rpsStatus';

// Polling hanya cadangan: event workflow (§17) memicu pembaruan lebih cepat bila tersedia.
const POLL_MS = 3000;

// Bila GET /rps menjawab 501 (backend lama sebelum BE-08.3), daftar memakai RPS yang diunggah pada sesi ini.
const listOrUnavailable = () =>
  listRps()
    .then((data) => ({ ...data, fetchedAt: Date.now() }))
    .catch((error) => {
      if (error?.status === 501) return { items: [], unavailable: true, fetchedAt: Date.now() };
      throw error;
    });

const byNewest = (a, b) => String(b.created_at ?? '').localeCompare(String(a.created_at ?? ''));

/**
 * Daftar RPS milik dosen (GET /rps) dengan status yang diperbarui otomatis:
 * event workflow memicu GET /rps/{id} untuk RPS terkait, dan polling berkala menjadi cadangan
 * sampai setiap RPS ANALYZED atau FAILED. `progress` menyimpan tahap workflow terakhir per RPS.
 */
export function useRpsLibrary() {
  const list = useApi(listOrUnavailable);
  // Data terbaru per RPS (dari upload, GET /rps/{id}, atau aksi) yang menimpa item daftar.
  const [local, setLocal] = useState({});
  const [progress, setProgress] = useState({});
  const [highlightId, setHighlightId] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [actionError, setActionError] = useState(null);
  const unavailable = !!list.data?.unavailable;
  const reloadList = list.reload;

  const items = useMemo(() => {
    const fetchedAt = list.data?.fetchedAt ?? 0;
    const merged = new Map((list.data?.items ?? []).map((item) => [item.id, item]));
    // Data yang lebih baru menang: patch lokal setelah daftar dimuat menimpa item daftar;
    // patch yang lebih lama hanya melengkapi field yang tidak ada di daftar (mis. pesan error).
    Object.values(local).forEach(({ updatedAt, ...patch }) => {
      const server = merged.get(patch.id);
      merged.set(patch.id, !server || updatedAt > fetchedAt ? { ...server, ...patch } : { ...patch, ...server });
    });
    return [...merged.values()].sort(byNewest);
  }, [list.data, local]);

  const remember = useCallback((id, patch) => {
    setLocal((current) => ({ ...current, [id]: { ...current[id], ...patch, id, updatedAt: Date.now() } }));
  }, []);

  /** Ambil status dokumen dari GET /rps/{id} (§6.2). Perubahan status memuat ulang daftar untuk workflow_id. */
  const refreshOne = useCallback(async (item) => {
    const detail = await getRps(item.id).catch(() => null);
    if (!detail) return;
    remember(item.id, detail);
    if (detail.status !== item.status && !unavailable) reloadList({ silent: true });
  }, [remember, unavailable, reloadList]);

  // GET /rps tidak memuat processing_error_message; ambil sekali dari GET /rps/{id} untuk RPS yang gagal.
  const failedFetched = useRef(new Set());
  useEffect(() => {
    items
      .filter((item) => item.status === RPS_STATUS.FAILED && !item.processing_error_message && !failedFetched.current.has(item.id))
      .forEach((item) => {
        failedFetched.current.add(item.id);
        refreshOne(item);
      });
  }, [items, refreshOne]);

  const pending = items.filter(isRpsInProgress);
  usePolling(() => Promise.all(pending.map(refreshOne)), POLL_MS, pending.length > 0);

  useWorkflowEvents(pending.map((item) => item.workflow_id), (event) => {
    const item = items.find((candidate) => candidate.workflow_id === event.workflow_id);
    if (!item) return;
    setProgress((current) => ({ ...current, [item.id]: { stage: event.stage, progress: event.progress, message: event.message, event: event.event } }));
    refreshOne(item);
  });

  /** Dipanggil RpsUploadForm setelah file tersimpan di server. */
  const addUploaded = useCallback(({ rps, processing: started }) => {
    remember(rps.id, {
      filename: rps.filename,
      status: started?.status ?? rps.status,
      created_at: rps.created_at ?? new Date().toISOString(),
      ...(started?.workflow_id ? { workflow_id: started.workflow_id } : {}),
    });
    setHighlightId(rps.id);
    reloadList({ silent: true });
  }, [remember, reloadList]);

  const run = useCallback(async (item, action) => {
    setBusyId(item.id);
    setActionError(null);
    try {
      const result = await action(item.id);
      setProgress((current) => ({ ...current, [item.id]: null }));
      remember(item.id, {
        status: result.status,
        processing_error_code: null,
        processing_error_message: null,
        ...(result.workflow_id ? { workflow_id: result.workflow_id } : {}),
      });
      await reloadList({ silent: true });
    } catch (error) {
      setActionError(error);
    } finally {
      setBusyId(null);
    }
  }, [remember, reloadList]);

  return {
    items,
    progress,
    loading: list.loading && !list.data,
    error: list.error,
    unavailable,
    highlightId,
    busyId,
    actionError,
    clearActionError: () => setActionError(null),
    addUploaded,
    /** Konversi (ulang) dokumen yang belum punya source_document: POST /rps/{id}/process. */
    process: (item) => run(item, processRps),
    /** Analisis (ulang) dari source_document: POST /rps/{id}/reanalyze (§6.6), juga untuk PROCESSED tanpa workflow. */
    reanalyze: (item) => run(item, reanalyzeRps),
    reload: () => reloadList(),
  };
}
