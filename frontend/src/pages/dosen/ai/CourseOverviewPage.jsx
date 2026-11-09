import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { getAgentRuns } from '../../../services/courseService';
import { generateWorkflowPlan } from '../../../services/coursePlanService';
import { COURSE_ACTIONS_AVAILABLE } from '../../../services/config';
import { useAction, useApi } from '../../../hooks/useApi';
import { Alert, Badge, Card, ErrorAlert, ProgressBar, Spinner } from '../../../components/ui';
import EventLog from '../../../components/ai/EventLog';
import ActivityConfigForm from '../../../components/ai/course/ActivityConfigForm';
import { RUN_TYPE_LABELS, isBusy } from '../../../utils/workflow';
import { formatDateTime } from '../../../utils/format';

// Langkah berikutnya yang perlu dilakukan dosen untuk tiap status.
const NEXT_STEP = {
  CREATED: { text: 'Minta agent menyusun rencana 16 minggu dari RPS.' },
  DRAFT: { text: 'Rencana dan konten course telah dibuat. Buka rencana untuk memeriksa.', to: 'plan', cta: 'Buka rencana' },
  WAITING_PLAN_REVIEW: { text: 'Rencana siap. Periksa lalu setujui atau minta revisi.', to: 'plan', cta: 'Review rencana' },
  PLAN_APPROVED: { text: 'Rencana disetujui. Lanjut generate konten mingguan.', to: 'content', cta: 'Generate konten' },
  WAITING_CONTENT_REVIEW: { text: 'Konten selesai divalidasi dan menunggu review Anda.', to: 'review', cta: 'Review konten' },
  CONTENT_REJECTED: { text: 'Konten ditolak. Regenerasi minggu yang bermasalah.', to: 'content', cta: 'Perbaiki konten' },
  APPROVED: { text: 'Konten disetujui dan siap dikirim ke Moodle.', to: 'publish', cta: 'Kirim ke Moodle' },
  EXECUTED: { text: 'Konten sudah terkirim. Jalankan verifikasi di Moodle.', to: 'publish', cta: 'Verifikasi' },
  COMPLETED: { text: 'Course selesai dibuat dan terverifikasi di Moodle.', to: 'publish', cta: 'Lihat hasil' },
};

export default function CourseOverviewPage() {
  const { course, workflow, workflowId, events, version, refresh } = useCourse();
  // GET /courses/{id}/agent-runs belum ada di backend; riwayat run hanya dimuat bila tersedia.
  const runs = useApi(() => (COURSE_ACTIONS_AVAILABLE ? getAgentRuns(course.id) : null), [course.id, version]);
  const plan = useAction(() => generateWorkflowPlan(workflowId));
  const busy = isBusy(course.status) || workflow?.status === 'RUNNING';
  const next = NEXT_STEP[course.status];
  const progress = workflow?.progress || course?.progress;
  const stage = workflow?.stage || course?.stage;

  const failureEvent = events?.slice().reverse().find(
    (e) => e.event === 'WORKFLOW_FAILED' || e.reason || (e.message && e.message.toLowerCase().includes('gagal')),
  );
  const failureMessage = failureEvent?.message || failureEvent?.reason || course?.processing_error_message;

  return (
    <div className="grid grid--2">
      <div className="stack">
        <Card title="Langkah berikutnya">
          <ErrorAlert error={plan.error} onClose={plan.clearError} />
          {failureMessage && (
            <div className="mb-3">
              <Alert tone="danger">
                <strong>Pemberitahuan alur kerja:</strong> {failureMessage}
              </Alert>
            </div>
          )}
          {busy ? (
            <>
              <p>Agent sedang bekerja. Halaman ini diperbarui otomatis.</p>
              {progress ? (
                <ProgressBar completed={progress.completed} total={progress.total} label={stage ?? ''} />
              ) : (
                <Spinner label={stage ?? 'Memproses…'} />
              )}
            </>
          ) : next ? (
            <div className="next-step">
              <p>{next.text}</p>
              {course.status === 'CREATED' ? (
                <button
                  type="button"
                  className="btn btn--primary"
                  disabled={!workflowId || plan.pending}
                  onClick={() => plan.run().then(refresh).catch(() => {})}
                >
                  {plan.pending ? 'Meminta…' : 'Generate rencana'}
                </button>
              ) : (
                <Link to={next.to} className="btn btn--primary">
                  {next.cta}
                </Link>
              )}
            </div>
          ) : (
            <p className="muted">Tidak ada aksi untuk status ini.</p>
          )}
        </Card>

        <Card title="Konfigurasi">
          <ActivityConfigForm course={course} onSaved={refresh} />
          {course.additional_prompt && (
            <div className="quote">
              <span className="field__label">Prompt tambahan</span>
              <p>{course.additional_prompt}</p>
            </div>
          )}
        </Card>
      </div>

      <div className="stack">
        <Card title="Aktivitas agent">
          <EventLog events={events} limit={15} />
        </Card>

        {COURSE_ACTIONS_AVAILABLE && (
        <Card title="Riwayat agent run">
          <ErrorAlert error={runs.error} />
          {runs.loading && !runs.data ? (
            <Spinner />
          ) : runs.data?.runs?.length ? (
            <ul className="list">
              {runs.data.runs.map((r) => (
                <li key={r.id} className="list__split">
                  <span>
                    {RUN_TYPE_LABELS[r.type] ?? r.type}
                    <small className="muted"> · {formatDateTime(r.started_at)}</small>
                  </span>
                  <Badge tone={r.status === 'completed' ? 'success' : r.status === 'running' ? 'info' : 'neutral'}>{r.status}</Badge>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">Belum ada agent run.</p>
          )}
        </Card>
        )}
      </div>
    </div>
  );
}
