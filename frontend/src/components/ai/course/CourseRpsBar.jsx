import { Link } from 'react-router-dom';
import { useApi } from '../../../hooks/useApi';
import { usePolling } from '../../../hooks/usePolling';
import { getRps } from '../../../services/rpsService';
import { findWorkflowForCourse, getActiveCourseBinding, getWorkflow, getWorkflowEvents } from '../../../services/workflowService';
import { RPS_STATUS, rpsStatusMeta } from '../../../utils/rpsStatus';
import {
  AWAITED_ACTION,
  STAGE_LABELS,
  WORKFLOW_API_STATUS,
  awaitedActionOf,
  isWorkflowBusy,
} from '../../../utils/workflowStatus';
import RpsStatusBadge from '../RpsStatusBadge';
import ActivityIcon from '../../moodle/ActivityIcon';
import { Badge, Spinner } from '../../ui';
import { COURSE_CARD } from '../../moodle/course/courseCard';

// Selama generator berjalan, status di kartu kursus diperbarui berkala (tanpa WebSocket di halaman kursus).
const BUSY_POLL_MS = 15000;

/** Status generator untuk dosen di halaman kursus: sedang berjalan, menunggu review, atau gagal. */
function GeneratorStatus({ base, workflow, events }) {
  if (!workflow) return null;
  if (isWorkflowBusy(workflow)) {
    return (
      <div className="flex w-full flex-wrap items-center gap-2 border-t border-line-subtle pt-3 text-sm" role="status">
        <Spinner size="sm" />
        <span className="min-w-0 flex-1">
          Generator AI sedang menyusun materi: <strong>{STAGE_LABELS[workflow.stage] ?? 'memproses'}</strong>
          {workflow.progress?.total > 0 && ` (${workflow.progress.completed}/${workflow.progress.total})`}
        </span>
        <Link to={`${base}/content`} className="btn btn--ghost btn--sm">Pantau</Link>
      </div>
    );
  }
  if (workflow.status === WORKFLOW_API_STATUS.FAILED) {
    return (
      <div className="flex w-full flex-wrap items-center gap-2 border-t border-line-subtle pt-3 text-sm">
        <Badge tone="danger">Generator berhenti</Badge>
        <span className="min-w-0 flex-1 text-muted">Proses berhenti karena kesalahan. Buka Generator AI untuk melanjutkan.</span>
        <Link to={base} className="btn btn--ghost btn--sm">Buka Generator AI</Link>
      </div>
    );
  }
  const action = awaitedActionOf(workflow, events);
  if (action === AWAITED_ACTION.REVIEW_CONTENT || action === AWAITED_ACTION.REVISE_CONTENT || action === AWAITED_ACTION.EXECUTE_FULL) {
    return (
      <div className="flex w-full flex-wrap items-center gap-2 border-t border-line-subtle pt-3 text-sm">
        <Badge tone="warning">Materi siap ditinjau</Badge>
        <span className="min-w-0 flex-1 text-muted">Tinjau materi mingguan hasil AI, lalu publikasikan ke kursus ini.</span>
        <Link to={`${base}/review`} className="btn btn--primary btn--sm">Tinjau &amp; publikasikan</Link>
      </div>
    );
  }
  if (action === AWAITED_ACTION.REVIEW_PLAN || action === AWAITED_ACTION.REVISE_PLAN || action === AWAITED_ACTION.START_PLANNING) {
    return (
      <div className="flex w-full flex-wrap items-center gap-2 border-t border-line-subtle pt-3 text-sm">
        <Badge tone="warning">Rencana perlu ditinjau</Badge>
        <span className="min-w-0 flex-1 text-muted">Rencana mingguan belum dapat disetujui otomatis. Periksa temuannya di Generator AI.</span>
        <Link to={`${base}/plan`} className="btn btn--primary btn--sm">Buka Rencana</Link>
      </div>
    );
  }
  return null;
}

/**
 * Kartu teratas tab Kursus untuk dosen, bergaya kartu aktivitas LMS ITK: RPS kursus ini (GET /rps/{id}) dengan
 * tautan ke halaman RPS dan hasil analisisnya, serta status Generator AI (berjalan, materi siap ditinjau). RPS
 * diambil dari binding aktif, metadata kursus, atau workflow yang menargetkan kursus ini.
 */
export default function CourseRpsBar({ course }) {
  const courseKeys = [course?.id, course?.moodle_course_id, course?.shortname, course?.code].filter(Boolean);
  const bound = getActiveCourseBinding(...courseKeys);
  const boundRpsId = bound?.rpsId;
  const boundWorkflowId = bound?.workflowId;

  const { data, loading, reload } = useApi(async () => {
    const workflow = boundWorkflowId
      ? await getWorkflow(boundWorkflowId).catch(() => null)
      : await findWorkflowForCourse(...courseKeys).catch(() => null);
    const rpsId = boundRpsId ?? course?.rps_id ?? workflow?.rps_id;
    const [rps, events] = await Promise.all([
      rpsId ? getRps(rpsId).catch(() => ({ id: rpsId })) : null,
      workflow ? getWorkflowEvents(workflow.id).catch(() => []) : [],
    ]);
    return { rps, workflow, events };
  }, [course?.id, course?.moodle_course_id, course?.shortname, course?.code, course?.rps_id, boundRpsId, boundWorkflowId]);

  usePolling(() => reload({ silent: true }), BUSY_POLL_MS, isWorkflowBusy(data?.workflow));

  if (loading && !data) return null;
  const base = `/course/${course.id}/ai`;
  const rps = data?.rps;

  if (!rps) {
    return (
      <div className={`${COURSE_CARD} flex flex-wrap items-center gap-3`} aria-label="RPS kursus">
        <ActivityIcon modname="resource" boxed />
        <span className="min-w-0 flex-1 text-sm text-muted">
          Kursus ini belum memiliki RPS. Unggah RPS, lalu Generator AI menyusun rencana dan materi setiap minggu.
        </span>
        <Link to={`${base}/rps`} className="btn btn--primary btn--sm">Unggah RPS</Link>
      </div>
    );
  }

  const analyzed = rps.status === RPS_STATUS.ANALYZED;
  const rpsPath = `${base}/rps?rps=${encodeURIComponent(rps.id)}`;
  return (
    <div className={`${COURSE_CARD} flex flex-wrap items-center gap-3`} aria-label="RPS kursus">
      <ActivityIcon modname="resource" boxed />
      <div className="min-w-0 flex-1">
        <Link to={rpsPath} className="font-semibold">Rencana Pembelajaran Semester (RPS)</Link>
        <div className="mt-0.5 flex flex-wrap items-center gap-2 text-sm text-muted">
          <span className="wrap-anywhere">{rps.filename ?? 'RPS'}</span>
          {rps.status && <RpsStatusBadge status={rps.status} />}
        </div>
      </div>
      {analyzed ? (
        <Link to={`${rpsPath}&bagian=hasil`} className="btn btn--ghost btn--sm">Hasil analisis</Link>
      ) : (
        <button type="button" className="btn btn--ghost btn--sm" disabled title={rpsStatusMeta(rps.status).description}>
          Hasil analisis
        </button>
      )}
      <GeneratorStatus base={base} workflow={data?.workflow} events={data?.events ?? []} />
    </div>
  );
}
