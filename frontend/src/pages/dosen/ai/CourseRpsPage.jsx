import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { useWorkflowMonitor } from '../../../hooks/useWorkflowMonitor';
import { getRps, getRpsAnalysis, processRps, reanalyzeRps } from '../../../services/rpsService';
import { generateWorkflowPlan, getWorkflowPlan } from '../../../services/coursePlanService';
import { COURSE_API_AVAILABLE } from '../../../services/config';
import { useAction, useApi } from '../../../hooks/useApi';
import { useOnChange } from '../../../hooks/useOnChange';
import { usePolling } from '../../../hooks/usePolling';
import { Card, ErrorAlert, Spinner } from '../../../components/ui';
import RpsStatusBadge from '../../../components/ai/RpsStatusBadge';
import RpsAnalysisDetails from '../../../components/ai/course/RpsAnalysisDetails';
import RpsUploadForm from '../../../components/ai/RpsUploadForm';
import { normalizeRpsAnalysis } from '../../../utils/rpsAnalysis';
import { RPS_STATUS, isRpsInProgress, rpsStatusMeta } from '../../../utils/rpsStatus';
import { formatDateTime } from '../../../utils/format';
import { WORKFLOW_EVENT, coursePlanProgressOf } from '../../../utils/workflowStatus';

const POLL_MS = 3000;
const RPS_REFRESH_DEBOUNCE_MS = 300;

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

/**
 * Tombol lanjut ke Course Planning (FE-12.1): memulai penyusunan lewat POST /workflows/{id}/plan lalu membuka
 * tab Rencana, yang menampilkan progresnya. Bila workflow sudah punya course plan atau sedang menyusunnya,
 * tombol membuka tab Rencana saja.
 */
function CoursePlanningAction({ analyzed, workflowId, planPath, planning }) {
  const navigate = useNavigate();
  const existing = useApi(() => (analyzed && workflowId ? getWorkflowPlan(workflowId).catch(() => null) : null), [analyzed, workflowId]);
  const generate = useAction(() => generateWorkflowPlan(workflowId), { loadingLabel: 'Memulai course planning…' });
  // 409: workflow sudah punya rencana atau sedang menyusunnya; tab Rencana menampilkan keadaannya.
  const openPlan = () => navigate(planPath, { relative: 'path' });
  const start = () => generate.run().then(openPlan, (e) => e?.status === 409 && openPlan());

  if (analyzed && workflowId && (existing.data || planning)) {
    return <Link to={planPath} relative="path" className="btn btn--primary">{planning ? 'Lihat progres Course Planning' : 'Lihat Course Plan'}</Link>;
  }
  const disabled = !analyzed || !workflowId || existing.loading || generate.pending;
  const hint = !analyzed ? 'Tersedia setelah RPS selesai dianalisis.' : !workflowId ? 'Course planning belum dapat dimulai untuk RPS ini.' : null;
  return (
    <span className="flex flex-col items-end gap-1">
      <button type="button" className="btn btn--primary" disabled={disabled} aria-describedby={hint ? 'planning-hint' : undefined} onClick={start}>
        {generate.pending ? 'Memulai…' : 'Lanjut ke Course Planning'}
      </button>
      {hint && <span id="planning-hint" className="text-xs text-muted">{hint}</span>}
      <ErrorAlert error={generate.error} onClose={generate.clearError} />
    </span>
  );
}

/** Hasil analisis RPS. */
export default function CourseRpsPage() {
  const { course, events = [], refresh, workflowId: projectWorkflowId, selectRps } = useCourse();
  // ?rps=<id> dari daftar RPS membuka RPS itu; RPS yang baru diunggah dari halaman ini didahulukan.
  const [params] = useSearchParams();
  const [activeRpsId, setActiveRpsId] = useState(null);
  const rpsId = activeRpsId || params.get('rps') || course.rps_id;
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
  const workflowId = rps?.workflow_id ?? (COURSE_API_AVAILABLE ? course.workflow_id : course.id);
  const hasProject = !!course.id;
  // Tab Rencana memakai workflow project; workflow RPS lain diteruskan lewat ?workflow= (dan ?rps= tanpa project).
  const planSearch = workflowId && workflowId !== projectWorkflowId
    ? `?${new URLSearchParams({ ...(hasProject ? {} : { rps: rps?.id ?? '' }), workflow: workflowId })}`
    : '';
  const planning = !!coursePlanProgressOf(monitor.workflow, monitor.events);

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
            onUploaded={async ({ rps: newRps }) => {
              if (newRps?.id) {
                setActiveRpsId(newRps.id);
                // Tanpa project kursus, RPS yang diunggah di sini menjadi RPS kursus ini.
                selectRps?.(newRps.id);
              }
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
          {/* Status workflow ada di tab Workflow; tanpa project kursus, RPS dibuka dari daftar RPS. */}
          {!hasProject && <Link to=".." relative="path" className="btn btn--ghost btn--sm">Kembali ke daftar RPS</Link>}
          {workflowId && (
            <Link to={`../workflows?workflow=${workflowId}`} relative="path" className="btn btn--ghost btn--sm">Pantau workflow</Link>
          )}
          <CoursePlanningAction analyzed={analyzed} workflowId={workflowId} planPath={`../plan${planSearch}`} planning={planning} />
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
          onChanged={async (newRps) => {
            if (newRps?.id) {
              setActiveRpsId(newRps.id);
              selectRps?.(newRps.id);
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
