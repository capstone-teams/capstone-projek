import { useCallback, useMemo, useState } from 'react';
import { useApi } from './useApi';
import { usePolling } from './usePolling';
import { RPS_IN_PROGRESS, getRps, listRps, processRps } from '../services/rpsService';

const POLL_MS = 2000;

// GET /rps masih stub 501 di backend sampai BE-08.3; daftar lalu memakai RPS yang diunggah pada sesi ini.
const listOrUnavailable = () =>
  listRps().catch((error) => {
    if (error?.status === 501) return { items: [], unavailable: true };
    throw error;
  });

const byNewest = (a, b) => String(b.created_at ?? '').localeCompare(String(a.created_at ?? ''));

/**
 * Daftar RPS milik dosen (GET /rps) beserta RPS yang baru diunggah, dipantau selama masih diproses.
 * workflow_id disimpan dari response pemrosesan bila ada, dan dari daftar backend (§6.5).
 */
export function useRpsLibrary() {
  const list = useApi(listOrUnavailable);
  const [recent, setRecent] = useState([]);
  const [highlightId, setHighlightId] = useState(null);
  const [processing, setProcessing] = useState(null);
  const [actionError, setActionError] = useState(null);
  const unavailable = !!list.data?.unavailable;

  const items = useMemo(() => {
    const server = list.data?.items ?? [];
    const merged = new Map(server.map((item) => [item.id, item]));
    for (const item of recent) {
      const known = merged.get(item.id);
      merged.set(item.id, known ? { ...known, workflow_id: known.workflow_id ?? item.workflow_id ?? null } : item);
    }
    return [...merged.values()].sort(byNewest);
  }, [list.data, recent]);

  const remember = useCallback((id, patch) => {
    setRecent((current) => {
      const existing = current.find((item) => item.id === id);
      return existing ? current.map((item) => (item.id === id ? { ...item, ...patch } : item)) : [{ id, ...patch }, ...current];
    });
  }, []);

  const refresh = useCallback(async () => {
    if (!unavailable) return list.reload({ silent: true });
    // Tanpa GET /rps: pantau status tiap RPS sesi ini lewat GET /rps/{id} (§6.2).
    const pending = recent.filter((item) => RPS_IN_PROGRESS.includes(item.status));
    const details = await Promise.all(pending.map((item) => getRps(item.id).catch(() => null)));
    details.filter(Boolean).forEach((detail) => remember(detail.id, detail));
    return null;
  }, [unavailable, list, recent, remember]);

  usePolling(refresh, POLL_MS, items.some((item) => RPS_IN_PROGRESS.includes(item.status)));

  /** Dipanggil RpsUploadForm setelah file tersimpan di server. */
  const addUploaded = useCallback(({ rps, processing: started }) => {
    remember(rps.id, {
      filename: rps.filename,
      status: started?.status ?? rps.status,
      created_at: rps.created_at ?? new Date().toISOString(),
      workflow_id: started?.workflow_id ?? null,
    });
    setHighlightId(rps.id);
    list.reload({ silent: true });
  }, [remember, list]);

  /** Proses (ulang) RPS yang belum diproses atau gagal. */
  const process = useCallback(async (item) => {
    setProcessing(item.id);
    setActionError(null);
    try {
      const started = await processRps(item.id);
      remember(item.id, { ...item, status: started.status, workflow_id: started.workflow_id ?? item.workflow_id ?? null });
      await list.reload({ silent: true });
    } catch (error) {
      setActionError(error);
    } finally {
      setProcessing(null);
    }
  }, [remember, list]);

  return {
    items,
    loading: list.loading && !list.data,
    error: list.error,
    unavailable,
    highlightId,
    processingId: processing,
    actionError,
    clearActionError: () => setActionError(null),
    addUploaded,
    process,
    reload: () => list.reload(),
  };
}
