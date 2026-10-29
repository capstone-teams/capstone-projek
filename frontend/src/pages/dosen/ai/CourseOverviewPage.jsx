import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { generatePlan, getAgentRuns } from '../../../services/courseService';
import { useAction, useApi } from '../../../hooks/useApi';
import { Badge, Card, ErrorAlert, ProgressBar, Spinner } from '../../../components/ui';
import EventLog from '../../../components/ai/EventLog';
import ActivityConfigForm from '../../../components/ai/course/ActivityConfigForm';
import { RUN_TYPE_LABELS, isBusy } from '../../../utils/workflow';
import { formatDateTime } from '../../../utils/format';

// Langkah berikutnya yang perlu dilakukan dosen untuk tiap status.
const NEXT_STEP = {
  CREATED: { text: 'Minta agent menyusun rencana 16 minggu dari RPS.' },
  WAITING_PLAN_REVIEW: { text: 'Rencana siap. Periksa lalu setujui atau minta revisi.', to: 'plan', cta: 'Review rencana' },
  PLAN_APPROVED: { text: 'Rencana disetujui. Lanjut generate konten mingguan.', to: 'content', cta: 'Generate konten' },
  WAITING_CONTENT_REVIEW: { text: 'Konten selesai divalidasi dan menunggu review Anda.', to: 'review', cta: 'Review konten' },
  CONTENT_REJECTED: { text: 'Konten ditolak. Regenerasi minggu yang bermasalah.', to: 'content', cta: 'Perbaiki konten' },
  APPROVED: { text: 'Konten disetujui dan siap dikirim ke Moodle.', to: 'publish', cta: 'Kirim ke Moodle' },
  EXECUTED: { text: 'Konten sudah terkirim. Jalankan verifikasi di Moodle.', to: 'publish', cta: 'Verifikasi' },
  COMPLETED: { text: 'Course selesai dibuat dan terverifikasi di Moodle.', to: 'publish', cta: 'Lihat hasil' },
};

export default function CourseOverviewPage() {
  const { course, events, version, refresh } = useCourse();
  const runs = useApi(() => getAgentRuns(course.id), [course.id, version]);
  const plan = useAction(generatePlan);
  const busy = isBusy(course.status);
  const next = NEXT_STEP[course.status];

  return (
    <div className="grid grid--2">
      <div className="stack">
        <Card title="Langkah berikutnya">
          <ErrorAlert error={plan.error} onClose={plan.clearError} />
          {busy ? (
            <>
              <p>Agent sedang bekerja. Halaman ini diperbarui otomatis.</p>
              {course.progress ? (
                <ProgressBar completed={course.progress.completed} total={course.progress.total} label={course.stage ?? ''} />
              ) : (
                <Spinner label={course.stage ?? 'Memproses…'} />
              )}
            </>
          ) : next ? (
            <div className="next-step">
              <p>{next.text}</p>
              {course.status === 'CREATED' ? (
                <button
                  type="button"
                  className="btn btn--primary"
                  disabled={plan.pending}
                  onClick={() => plan.run(course.id).then(refresh).catch(() => {})}
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

        <Card title="Riwayat agent run">
          <ErrorAlert error={runs.error} />
          {runs.loading && !runs.data ? (
            <Spinner />
          ) : runs.data?.runs.length ? (
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
      </div>
    </div>
  );
}
