import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { getRps, getRpsAnalysis, processRps, reanalyzeRps } from '../../../services/rpsService';
import { USE_MOCK } from '../../../services/config';
import { useApi } from '../../../hooks/useApi';
import { usePolling } from '../../../hooks/usePolling';
import { Card, ErrorAlert, Spinner } from '../../../components/ui';
import RpsStatusBadge from '../../../components/ai/RpsStatusBadge';
import RpsAnalysisDetails from '../../../components/ai/course/RpsAnalysisDetails';
import { normalizeRpsAnalysis } from '../../../utils/rpsAnalysis';
import { RPS_STATUS, isRpsInProgress, rpsStatusMeta } from '../../../utils/rpsStatus';
import { formatDateTime } from '../../../utils/format';

// Course planning (FE-05) baru tersedia di backend pada M03; di mode mock sudah dapat dicoba.
const COURSE_PLANNING_AVAILABLE = USE_MOCK;
const POLL_MS = 3000;

/**
 * RPS yang belum ANALYZED: GET /rps/{id}/analysis menjawab 422, jadi tampilkan statusnya dan aksi
 * lanjutan (analisis lewat POST /rps/{id}/reanalyze, atau konversi ulang lewat POST /rps/{id}/process).
 */
function RpsNotAnalyzed({ rps, onChanged }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const meta = rpsStatusMeta(rps.status);
  const canAnalyze = rps.has_source_document && [RPS_STATUS.PROCESSED, RPS_STATUS.FAILED].includes(rps.status);
  const canProcess = !rps.has_source_document && [RPS_STATUS.UPLOADED, RPS_STATUS.FAILED].includes(rps.status);

  const run = async (action) => {
    setPending(true);
    setError(null);
    try {
      await action(rps.id);
      await onChanged();
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  };

  return (
    <Card title="Hasil analisis belum tersedia">
      <ErrorAlert error={error} onClose={() => setError(null)} />
      <p className="text-sm" aria-live="polite">
        {meta.description}
        {isRpsInProgress(rps) && ' Status diperbarui otomatis.'}
      </p>
      {rps.status === RPS_STATUS.FAILED && (
        <p className="mt-2 text-sm text-danger" role="status">{rps.processing_error_message ?? 'Pemrosesan RPS gagal.'}</p>
      )}
      {(canAnalyze || canProcess) && (
        <button type="button" className="btn btn--primary mt-3" disabled={pending} onClick={() => run(canAnalyze ? reanalyzeRps : processRps)}>
          {pending ? 'Memulai…' : canProcess ? 'Proses ulang' : rps.status === RPS_STATUS.FAILED ? 'Analisis ulang' : 'Analisis RPS'}
        </button>
      )}
    </Card>
  );
}

/** Hasil Analisis RPS (FE-08.3): diperiksa dosen sebelum melanjutkan ke course planning. */
export default function CourseRpsPage() {
  const { course } = useCourse();
  const rpsId = course.rps_id;
  // Status dulu (GET /rps/{id}); hasil analisis hanya diminta bila sudah ANALYZED.
  const rpsQuery = useApi(() => getRps(rpsId), [rpsId]);
  const rps = rpsQuery.data;
  const analyzed = rps?.status === RPS_STATUS.ANALYZED;
  const analysisQuery = useApi(() => (analyzed ? getRpsAnalysis(rpsId) : null), [rpsId, analyzed]);
  const analysis = useMemo(() => (analysisQuery.data ? normalizeRpsAnalysis(analysisQuery.data) : null), [analysisQuery.data]);
  usePolling(() => rpsQuery.reload({ silent: true }), POLL_MS, !!rps && isRpsInProgress(rps));

  const error = rpsQuery.error ?? analysisQuery.error;
  if ((rpsQuery.loading && !rps) || (analyzed && analysisQuery.loading && !analysis)) return <Spinner label="Memuat hasil analisis…" />;
  if (error) {
    return (
      <div>
        <ErrorAlert error={error} />
        <button type="button" className="btn" onClick={() => (rpsQuery.error ? rpsQuery.reload() : analysisQuery.reload())}>Coba lagi</button>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl">Hasil analisis RPS</h2>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted">
            <span className="wrap-anywhere">{rps.filename}</span>
            <RpsStatusBadge status={rps.status} />
            {analysis?.analyzedAt && <span>Dianalisis {formatDateTime(analysis.analyzedAt)}</span>}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* Monitoring workflow kursus ini ada di tab Ringkasan (Aktivitas agent). */}
          <Link to=".." relative="path" className="btn btn--ghost btn--sm">
            Pantau workflow
          </Link>
          {COURSE_PLANNING_AVAILABLE && analyzed ? (
            <Link to="../plan" relative="path" className="btn btn--primary">
              Lanjut ke Course Planning
            </Link>
          ) : (
            <span className="flex flex-col items-end gap-1">
              <button type="button" className="btn btn--primary" disabled aria-describedby="planning-hint">
                Lanjut ke Course Planning
              </button>
              <span id="planning-hint" className="text-xs text-muted">
                {analyzed ? 'Course planning aktif pada M03.' : 'Tersedia setelah RPS selesai dianalisis.'}
              </span>
            </span>
          )}
        </div>
      </div>

      {analysis ? <RpsAnalysisDetails analysis={analysis} /> : <RpsNotAnalyzed rps={rps} onChanged={() => rpsQuery.reload({ silent: true })} />}
    </div>
  );
}
