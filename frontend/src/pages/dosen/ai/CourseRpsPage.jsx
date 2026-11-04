import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { useWorkflow } from '../../../hooks/useWorkflow';
import { getRps, getRpsAnalysis, processRps, reanalyzeRps } from '../../../services/rpsService';
import { COURSE_API_AVAILABLE } from '../../../services/config';
import { useApi } from '../../../hooks/useApi';
import { usePolling } from '../../../hooks/usePolling';
import { Card, ErrorAlert, Spinner } from '../../../components/ui';
import RpsStatusBadge from '../../../components/ai/RpsStatusBadge';
import RpsAnalysisDetails from '../../../components/ai/course/RpsAnalysisDetails';
import RpsUploadForm from '../../../components/ai/RpsUploadForm';
import { normalizeRpsAnalysis } from '../../../utils/rpsAnalysis';
import { RPS_STATUS, isRpsInProgress, rpsStatusMeta } from '../../../utils/rpsStatus';
import { formatDateTime } from '../../../utils/format';

// Course planning (FE-05) baru tersedia di backend pada M03; di mode mock sudah dapat dicoba.
const COURSE_PLANNING_AVAILABLE = COURSE_API_AVAILABLE;
const POLL_MS = 3000;

/**
 * RPS yang belum ANALYZED: GET /rps/{id}/analysis menjawab 422, jadi tampilkan statusnya dan aksi
 * lanjutan (analisis lewat POST /rps/{id}/reanalyze, atau konversi ulang lewat POST /rps/{id}/process).
 */
function RpsNotAnalyzed({ rps, events = [], onChanged }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const [showUpload, setShowUpload] = useState(false);
  const meta = rpsStatusMeta(rps.status);
  const canAnalyze = rps.has_source_document && [RPS_STATUS.PROCESSED, RPS_STATUS.FAILED].includes(rps.status);
  const canProcess = !rps.has_source_document && [RPS_STATUS.UPLOADED, RPS_STATUS.FAILED].includes(rps.status);

  const failureEvent = events?.slice()?.reverse()?.find((e) => e.event === 'WORKFLOW_FAILED' || e.message?.toLowerCase().includes('gagal'));
  const failureMessage = failureEvent?.message || rps.processing_error_message || 'Pemrosesan RPS gagal.';

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
        <div className="alert alert--danger mt-3" role="status">
          <p className="font-medium">Diagnostik kegagalan:</p>
          <p className="mt-1 text-sm">{failureMessage}</p>
        </div>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {(canAnalyze || canProcess) && (
          <button type="button" className="btn btn--primary" disabled={pending} onClick={() => run(canAnalyze ? reanalyzeRps : processRps)}>
            {pending ? 'Memulai…' : canProcess ? 'Proses ulang' : rps.status === RPS_STATUS.FAILED ? 'Analisis ulang' : 'Analisis RPS'}
          </button>
        )}
        <button
          type="button"
          className="btn btn--secondary"
          onClick={() => setShowUpload((s) => !s)}
        >
          {showUpload ? 'Tutup form upload' : 'Unggah dokumen RPS baru'}
        </button>
      </div>

      {showUpload && (
        <div className="mt-4 border-t pt-4">
          <h3 className="mb-2 text-sm font-medium">Unggah berkas RPS baru:</h3>
          <RpsUploadForm
            onUploaded={async ({ rps: newRps, error: uploadErr }) => {
              if (!uploadErr && newRps) {
                setShowUpload(false);
                await onChanged(newRps);
              }
            }}
          />
        </div>
      )}
    </Card>
  );
}

/** Hasil analisis RPS. */
export default function CourseRpsPage() {
  const { course } = useCourse();
  const rpsId = course.rps_id;
  // Pada backend nyata `course` adalah workflow itu sendiri; pada mock /courses itu project, jadi tanpa id workflow.
  const workflowId = COURSE_API_AVAILABLE ? course.workflow_id : course.id;
  // Status dulu (GET /rps/{id}); hasil analisis hanya diminta bila sudah ANALYZED.
  const rpsQuery = useApi(() => (rpsId ? getRps(rpsId) : null), [rpsId]);
  const rps = rpsQuery.data;
  const analyzed = rps?.status === RPS_STATUS.ANALYZED;
  const analysisQuery = useApi(() => (analyzed ? getRpsAnalysis(rpsId) : null), [rpsId, analyzed]);
  const analysis = useMemo(() => (analysisQuery.data ? normalizeRpsAnalysis(analysisQuery.data) : null), [analysisQuery.data]);
  usePolling(() => rpsQuery.reload({ silent: true }), POLL_MS, !!rps && isRpsInProgress(rps));

  // Ambil event spesifik milik workflow RPS ini jika berbeda dari workflow course
  const rpsWorkflowId = rps?.workflow_id;
  const { events: rpsEvents } = useWorkflow(null, rpsWorkflowId);
  const effectiveEvents = rpsEvents?.length > 0 ? rpsEvents : events;

  const error = rpsQuery.error ?? analysisQuery.error;
  if ((rpsQuery.loading && !rps && rpsId) || (analyzed && analysisQuery.loading && !analysis)) return <Spinner label="Memuat hasil analisis…" />;
  if (error) {
    return (
      <div>
        <ErrorAlert error={error} />
        <button type="button" className="btn" onClick={() => (rpsQuery.error ? rpsQuery.reload() : analysisQuery.reload())}>Coba lagi</button>
      </div>
    );
  }

  if (!rps) {
    return (
      <Card title="Belum ada RPS terkait">
        <p className="text-muted text-sm">Kursus ini belum memiliki dokumen RPS yang diunggah.</p>
        <div className="mt-3">
          <RpsUploadForm
            onUploaded={async ({ rps: newRps }) => {
              if (newRps?.id) setActiveRpsId(newRps.id);
              refresh?.();
            }}
          />
        </div>
      </Card>
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
            {activeRpsId && activeRpsId !== course?.rps_id && (
              <button
                type="button"
                className="btn btn--ghost btn--xs"
                onClick={() => setActiveRpsId(null)}
              >
                Kembali ke RPS awal kursus
              </button>
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* Status workflow ada di tab Workflow; RPS tanpa workflow kembali ke daftar RPS. */}
          <Link to={course.id ? `../workflows${workflowId ? `?workflow=${workflowId}` : ''}` : '..'} relative="path" className="btn btn--ghost btn--sm">
            {course.id ? 'Pantau workflow' : 'Kembali ke daftar RPS'}
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

      {analysis ? (
        <RpsAnalysisDetails analysis={analysis} />
      ) : (
        <RpsNotAnalyzed
          rps={rps}
          events={effectiveEvents}
          onChanged={async (newRps) => {
            if (newRps?.id) {
              setActiveRpsId(newRps.id);
              refresh?.();
            } else {
              rpsQuery.reload({ silent: true });
            }
          }}
        />
      )}
    </div>
  );
}
