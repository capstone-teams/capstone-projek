import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { useWorkflowMonitor } from '../../../hooks/useWorkflowMonitor';
import { getRps, getRpsAnalysis, processRps, reanalyzeRps } from '../../../services/rpsService';
import { COURSE_API_AVAILABLE } from '../../../services/config';
import { useApi } from '../../../hooks/useApi';
import { useOnChange } from '../../../hooks/useOnChange';
import { usePolling } from '../../../hooks/usePolling';
import { Card, ErrorAlert, Spinner } from '../../../components/ui';
import RpsStatusBadge from '../../../components/ai/RpsStatusBadge';
import RpsAnalysisDetails from '../../../components/ai/course/RpsAnalysisDetails';
import RpsUploadForm from '../../../components/ai/RpsUploadForm';
import { normalizeRpsAnalysis } from '../../../utils/rpsAnalysis';
import { RPS_STATUS, isRpsInProgress, rpsStatusMeta } from '../../../utils/rpsStatus';
import { formatDateTime } from '../../../utils/format';
import { WORKFLOW_EVENT } from '../../../utils/workflowStatus';
import { moodleCourseIdOf, setWorkflowMoodleTarget } from '../../../services/workflowService';

// Course planning (FE-05) baru tersedia di backend pada M03; di mode mock sudah dapat dicoba.
const COURSE_PLANNING_AVAILABLE = COURSE_API_AVAILABLE;
const POLL_MS = 3000;
const RPS_REFRESH_DEBOUNCE_MS = 300;

/**
 * RPS yang belum ANALYZED: GET /rps/{id}/analysis menjawab 422, jadi tampilkan statusnya dan aksi
 * lanjutan (analisis lewat POST /rps/{id}/reanalyze, atau konversi ulang lewat POST /rps/{id}/process).
 */
function RpsNotAnalyzed({ rps, events = [], onChanged, moodleCourseId }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const [showUpload, setShowUpload] = useState(false);
  const meta = rpsStatusMeta(rps.status);
  const canAnalyze = rps.has_source_document && [RPS_STATUS.PROCESSED, RPS_STATUS.FAILED].includes(rps.status);
  const canProcess = !rps.has_source_document && [RPS_STATUS.UPLOADED, RPS_STATUS.FAILED].includes(rps.status);

  // Pesan resmi dari GET /rps/{id} lebih dulu; event WORKFLOW_FAILED terakhir hanya cadangan.
  const failureEvent = [...events].reverse().find((e) => e.event === WORKFLOW_EVENT.FAILED);
  const failureMessage = rps.processing_error_message || failureEvent?.message || 'Pemrosesan RPS gagal.';

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
            onUploaded={async ({ rps: newRps, processing, error: uploadErr }) => {
              if (!uploadErr && newRps) {
                setShowUpload(false);
                if (moodleCourseId) {
                  try {
                    sessionStorage.setItem(`agentic-lms.course-rps.${moodleCourseId}`, newRps.id);
                    const wfId = processing?.workflow_id || newRps.workflow_id;
                    if (wfId) {
                      sessionStorage.setItem(`agentic-lms.course-workflow.${moodleCourseId}`, wfId);
                      await setWorkflowMoodleTarget(wfId, moodleCourseId);
                    }
                  } catch {
                    // ignore
                  }
                }
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
  const { course, moodleCourse, events = [], refresh, initialRpsId } = useCourse();
  const moodleId = moodleCourseIdOf(course) || moodleCourseIdOf(moodleCourse);

  // ?rps=<id> dari daftar RPS membuka RPS itu; RPS yang baru diunggah dari halaman ini didahulukan.
  const [params] = useSearchParams();
  const [activeRpsId, setActiveRpsId] = useState(null);
  const rpsId = activeRpsId || params.get('rps') || course?.rps_id;
  // Status dulu (GET /rps/{id}); hasil analisis hanya diminta bila sudah ANALYZED.
  const rpsQuery = useApi(() => (rpsId ? getRps(rpsId) : null), [rpsId]);
  const rps = rpsQuery.data;
  const analyzed = rps?.status === RPS_STATUS.ANALYZED;
  const analysisQuery = useApi(() => (analyzed ? getRpsAnalysis(rpsId) : null), [rpsId, analyzed]);
  const analysis = useMemo(() => (analysisQuery.data ? normalizeRpsAnalysis(analysisQuery.data) : null), [analysisQuery.data]);

  // Status diperbarui lewat event workflow RPS ini (FE-10.2): setiap perubahan workflow memicu GET /rps/{id}.
  // Polling tetap berjalan sebagai cadangan selama pemrosesan belum berhenti.
  const monitor = useWorkflowMonitor(rps?.workflow_id);
  const workflowChange = monitor.workflow ? `${monitor.workflow.status}|${monitor.workflow.stage}|${monitor.workflow.updated_at}` : null;
  const { reload: reloadRps } = rpsQuery;
  // Event beruntun (puluhan event progres per tahap) digabung menjadi satu GET /rps/{id}.
  useOnChange(workflowChange, () => reloadRps({ silent: true }), RPS_REFRESH_DEBOUNCE_MS);
  usePolling(() => rpsQuery.reload({ silent: true }), POLL_MS, !!rps && isRpsInProgress(rps));
  const effectiveEvents = monitor.events.length > 0 ? monitor.events : events;
  // Workflow RPS dari GET /rps/{id}; project /courses di backend tidak memuat workflow_id.
  const workflowId = rps?.workflow_id ?? (COURSE_API_AVAILABLE ? course?.workflow_id : course?.id);
  const hasProject = Boolean(course?.id);

  // ?bagian=hasil (dari tombol "Hasil analisis" di tab Kursus): gulir ke hasil analisis setelah tampil.
  const jumpToResult = params.get('bagian') === 'hasil' && !!analysis;
  useEffect(() => {
    if (jumpToResult) document.getElementById('hasil-analisis')?.scrollIntoView({ block: 'start' });
  }, [jumpToResult]);

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
            onUploaded={async ({ rps: newRps, processing }) => {
              if (newRps?.id) {
                setActiveRpsId(newRps.id);
                if (moodleId) {
                  try {
                    sessionStorage.setItem(`agentic-lms.course-rps.${moodleId}`, newRps.id);
                    const wfId = processing?.workflow_id || newRps.workflow_id;
                    if (wfId) {
                      sessionStorage.setItem(`agentic-lms.course-workflow.${moodleId}`, wfId);
                      await setWorkflowMoodleTarget(wfId, moodleId);
                    }
                  } catch {
                    // ignore
                  }
                }
              }
              await refresh?.();
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
            {initialRpsId && initialRpsId !== rpsId && (
              <button
                type="button"
                className="btn btn--ghost btn--xs"
                onClick={() => {
                  if (moodleId) {
                    sessionStorage.removeItem(`agentic-lms.course-rps.${moodleId}`);
                    sessionStorage.removeItem(`agentic-lms.course-workflow.${moodleId}`);
                  }
                  setActiveRpsId(initialRpsId);
                  refresh?.();
                }}
              >
                Lihat RPS awal kursus
              </button>
            )}
            {activeRpsId && activeRpsId === initialRpsId && course?.rps_id !== initialRpsId && (
              <button
                type="button"
                className="btn btn--ghost btn--xs"
                onClick={() => {
                  setActiveRpsId(null);
                  refresh?.();
                }}
              >
                Kembali ke RPS aktif
              </button>
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* Status workflow ada di tab Workflow; tanpa project kursus, RPS dibuka dari daftar RPS. */}
          {!hasProject && <Link to=".." relative="path" className="btn btn--ghost btn--sm">Kembali ke daftar RPS</Link>}
          {workflowId && (
            <Link to={`../workflows?workflow=${workflowId}`} relative="path" className="btn btn--ghost btn--sm">Pantau workflow</Link>
          )}
          {COURSE_PLANNING_AVAILABLE && analyzed && hasProject ? (
            <Link to="../plan" relative="path" className="btn btn--primary">
              Lanjut ke Course Planning
            </Link>
          ) : (
            <span className="flex flex-col items-end gap-1">
              <button type="button" className="btn btn--primary" disabled aria-describedby="planning-hint">
                Lanjut ke Course Planning
              </button>
              <span id="planning-hint" className="text-xs text-muted">
                {!analyzed ? 'Tersedia setelah RPS selesai dianalisis.' : COURSE_PLANNING_AVAILABLE ? 'Mulai generator AI untuk kursus ini terlebih dahulu.' : 'Course planning aktif pada M03.'}
              </span>
            </span>
          )}
        </div>
      </div>

      {analysis ? (
        <div id="hasil-analisis" className="scroll-mt-4">
          <RpsAnalysisDetails analysis={analysis} />
        </div>
      ) : (
        <RpsNotAnalyzed
          rps={rps}
          events={effectiveEvents}
          moodleCourseId={moodleId}
          onChanged={async (newRps) => {
            if (newRps?.id) {
              setActiveRpsId(newRps.id);
              await refresh?.();
            } else {
              rpsQuery.reload({ silent: true });
            }
          }}
        />
      )}
    </div>
  );
}
