import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { useApi } from '../../../hooks/useApi';
import { getRps } from '../../../services/rpsService';
import { Alert, Badge, Card, ProgressBar, Spinner } from '../../../components/ui';
import RpsStatusBadge from '../../../components/ai/RpsStatusBadge';
import WorkflowConnectionNote from '../../../components/ai/WorkflowConnectionNote';
import WorkflowEventTimeline from '../../../components/ai/WorkflowEventTimeline';
import WorkflowStatusBadge from '../../../components/ai/WorkflowStatusBadge';
import {
  AWAITED_ACTION,
  AWAITED_ACTION_META,
  STAGE_LABELS,
  WORKFLOW_API_STATUS,
  WORKFLOW_EVENT,
  awaitedActionOf,
  isWorkflowBusy,
  needsInstructorAction,
  workflowStatusMeta,
} from '../../../utils/workflowStatus';

function quickTarget(page, workflow) {
  if (page !== 'plan' || !workflow?.id) return page;
  const params = new URLSearchParams({ workflow: workflow.id });
  if (workflow.rps_id) params.set('rps', workflow.rps_id);
  return `plan?${params}`;
}

export default function CourseOverviewPage() {
  const { course, moodleCourse, workflow, workflowId, events = [], contents = null, connection } = useCourse() ?? {};
  const activeWorkflow = workflow ?? null;
  const rpsId = activeWorkflow?.rps_id ?? course?.rps_id ?? null;
  const rps = useApi(() => (rpsId ? getRps(rpsId).catch(() => null) : null), [rpsId]);

  const targetCourse = moodleCourse ?? course;
  const targetMoodleId = course?.moodle_course_id ?? moodleCourse?.id ?? course?.id;
  const hasRps = Boolean(rpsId || activeWorkflow || workflowId);

  const busy = isWorkflowBusy(activeWorkflow);
  const waitingReview = needsInstructorAction(activeWorkflow);
  const hasPartialContents = Array.isArray(contents)
    && contents.length > 0
    && contents.some((item) => item?.status !== 'APPROVED' && item?.status !== 'EXECUTED');
  const awaitedAction = awaitedActionOf(activeWorkflow, events);
  const resolvedAction = waitingReview
    ? (hasPartialContents ? AWAITED_ACTION.REVIEW_CONTENT : awaitedAction)
    : null;
  const actionMeta = resolvedAction ? AWAITED_ACTION_META[resolvedAction] : null;
  const statusMeta = activeWorkflow ? workflowStatusMeta(activeWorkflow) : null;

  const failureEvent = activeWorkflow?.status === WORKFLOW_API_STATUS.FAILED
    ? [...events].reverse().find((e) => e.event === WORKFLOW_EVENT.FAILED)
    : null;
  const failureMessage = failureEvent?.message || course?.processing_error_message || 'Workflow berhenti karena kesalahan.';

  const hadFullExecution = events.some(
    (ev) => ev?.event === WORKFLOW_EVENT.MOODLE_OPERATION && / - (Learning Material|Learning Resource|Assignment|Quiz) /.test(ev.message ?? ''),
  );

  return (
    <div className="grid grid--2">
      <div className="stack">
        <Card title="Langkah berikutnya">
          {!hasRps ? (
            <div className="next-step">
              <p>Kursus ini belum memiliki dokumen RPS. Silakan unggah dokumen RPS untuk memulai penyusunan rencana pembelajaran.</p>
              <Link to="rps" className="btn btn--primary">Unggah RPS</Link>
            </div>
          ) : !activeWorkflow ? (
            <div className="next-step">
              <p>RPS terhubung ke kursus ini. Buka tab RPS untuk memeriksa hasil analisis dan memulai course planning.</p>
              <Link to="rps" className="btn btn--primary">Buka tab RPS</Link>
            </div>
          ) : activeWorkflow.status === WORKFLOW_API_STATUS.FAILED ? (
            <div className="stack">
              <Alert tone="danger" title="Workflow berhenti karena kesalahan">{failureMessage}</Alert>
              <div className="flex flex-wrap gap-2">
                <Link to="rps" className="btn btn--primary">Buka tab RPS</Link>
                <Link to="workflows" className="btn btn--ghost">Pantau workflow</Link>
              </div>
            </div>
          ) : activeWorkflow.status === WORKFLOW_API_STATUS.COMPLETED ? (
            <div className="next-step">
              <Alert tone="success" title="Seluruh tahap selesai">Generator AI telah menyelesaikan seluruh tahapan untuk kursus ini.</Alert>
              <Link to="publish" className="btn btn--primary">Lihat hasil publikasi</Link>
            </div>
          ) : busy ? (
            <div className="stack">
              <div className="flex flex-wrap items-center gap-2">
                <WorkflowStatusBadge workflow={activeWorkflow} />
                {statusMeta?.description && <span className="text-sm text-muted">{statusMeta.description}</span>}
              </div>
              {activeWorkflow.progress?.total > 0 ? (
                <ProgressBar
                  completed={activeWorkflow.progress.completed}
                  total={activeWorkflow.progress.total}
                  label={STAGE_LABELS[activeWorkflow.stage] ?? 'Memproses…'}
                />
              ) : (
                <Spinner label={STAGE_LABELS[activeWorkflow.stage] ?? 'Memproses…'} />
              )}
              <div>
                <Link to="workflows" className="btn btn--ghost btn--sm">Pantau workflow</Link>
              </div>
            </div>
          ) : waitingReview && actionMeta ? (
            <div className="next-step">
              <p>
                <strong>{actionMeta.title}</strong> — {actionMeta.description}
              </p>
              <div className="flex flex-wrap gap-2">
                <Link to={quickTarget(actionMeta.page, activeWorkflow)} className="btn btn--primary">
                  {actionMeta.linkLabel}
                </Link>
                {actionMeta.secondary && (
                  <Link to={quickTarget(actionMeta.secondary.page, activeWorkflow)} className="btn btn--ghost">
                    {actionMeta.secondary.label}
                  </Link>
                )}
              </div>
            </div>
          ) : hadFullExecution ? (
            <div className="next-step">
              <p>Eksekusi struktur dan konten ke Moodle sudah selesai. Anda dapat meninjau detail operasi dan riwayat eksekusi.</p>
              <Link to="publish" className="btn btn--primary">Buka halaman Publikasi</Link>
            </div>
          ) : (
            <div className="next-step">
              <p>Pantau progres terbaru dan riwayat eksekusi workflow kursus ini.</p>
              <Link to="workflows" className="btn btn--ghost">Pantau workflow</Link>
            </div>
          )}
        </Card>

        <Card title="Konfigurasi">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-line-subtle pb-3 text-xs">
            <span className="text-muted">Target Moodle:</span>
            <span className="font-semibold text-ink" aria-label="Target Moodle">
              {targetCourse?.code ?? targetCourse?.shortname ?? '-'} — {targetCourse?.name ?? targetCourse?.fullname ?? '-'} (ID: {targetMoodleId ?? '-'})
            </span>
          </div>
          {activeWorkflow && <WorkflowConnectionNote workflow={activeWorkflow} connection={connection} />}
          <dl className="dl mt-2">
            <dt>Status workflow</dt>
            <dd>{activeWorkflow ? <WorkflowStatusBadge workflow={activeWorkflow} /> : <Badge>Belum ada workflow</Badge>}</dd>
            <dt>RPS aktif</dt>
            <dd>
              {rps.data ? (
                <span className="flex flex-wrap items-center gap-2">
                  <Link to="rps">{rps.data.filename ?? rpsId}</Link>
                  {rps.data.status && <RpsStatusBadge status={rps.data.status} />}
                </span>
              ) : rpsId ? (
                <Link to="rps">Lihat detail RPS</Link>
              ) : (
                <span className="text-muted">Belum ada RPS</span>
              )}
            </dd>
          </dl>
          <div className="mt-4 border-t border-line-subtle pt-3 text-sm text-muted">
            Preferensi pengajaran dan generator konten diatur di{' '}
            <Link to="/profile" className="font-semibold text-primary underline">Profil dosen</Link>.
          </div>
        </Card>
      </div>

      <div className="stack">
        <Card title="Aktivitas agent">
          <WorkflowEventTimeline events={events} />
        </Card>
      </div>
    </div>
  );
}
