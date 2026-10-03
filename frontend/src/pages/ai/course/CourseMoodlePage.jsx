import { useState } from 'react';
import { useCourse } from '../../../hooks/useCourse';
import {
  cancelExecution,
  executeCourse,
  getExecution,
  getVerification,
  startVerification,
} from '../../../services/courseService';
import { MOODLE_URL } from '../../../services/config';
import { useAction, useApi } from '../../../hooks/useApi';
import { usePolling } from '../../../hooks/usePolling';
import { Alert, Badge, Card, EmptyState, ErrorAlert, Modal, ProgressBar, Spinner } from '../../../components/ui';
import { formatDateTime } from '../../../utils/format';

const BEFORE_APPROVAL = ['CREATED', 'PLANNING', 'WAITING_PLAN_REVIEW', 'PLAN_APPROVED', 'GENERATING_CONTENT', 'VALIDATING', 'WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED'];
const EXEC_TONES = { completed: 'success', failed: 'danger', cancelled: 'neutral', queued: 'info', running: 'info' };

function moodleCourseUrl(id) {
  if (!id) return MOODLE_URL;
  return /^\d+$/.test(id)
    ? `${MOODLE_URL}/course/view.php?id=${id}`
    : `${MOODLE_URL}/course/search.php?search=${encodeURIComponent(id)}`;
}

export default function CourseMoodlePage() {
  const { course } = useCourse();

  if (BEFORE_APPROVAL.includes(course.status)) {
    return (
      <Card>
        <EmptyState title="Konten belum disetujui.">
          Eksekusi ke Moodle hanya dapat dilakukan setelah seluruh konten direview dan disetujui.
        </EmptyState>
      </Card>
    );
  }

  return (
    <div className="grid grid--2">
      <ExecutionCard />
      <VerificationCard />
    </div>
  );
}

function ExecutionCard() {
  const { course, version, refresh } = useCourse();
  const executionId = course.latest_execution_id;
  const execution = useApi(() => (executionId ? getExecution(course.id, executionId) : null), [course.id, executionId, version]);
  const execute = useAction(() => executeCourse(course.id));
  const cancel = useAction(() => cancelExecution(course.id, executionId));
  const [confirming, setConfirming] = useState(false);

  const ex = execution.data;
  const running = ex && ['queued', 'running'].includes(ex.status);
  // Cadangan bila event WebSocket terlewat.
  usePolling(() => execution.reload({ silent: true }), 3000, !!running);

  return (
    <Card title="Eksekusi ke Moodle">
      <ErrorAlert error={execute.error || cancel.error || execution.error} onClose={() => {
          execute.clearError();
          cancel.clearError();
        }} />

      {course.status === 'APPROVED' && (
        <div className="next-step">
          <p>
            Backend akan membuat section, materi, dan aktivitas di course Moodle <strong>{course.moodle_course_id || '(baru)'}</strong>.
          </p>
          <button type="button" className="btn btn--primary" onClick={() => setConfirming(true)}>
            {ex ? 'Kirim ulang ke Moodle' : 'Kirim ke Moodle'}
          </button>
        </div>
      )}

      {execution.loading && !ex && executionId ? (
        <Spinner />
      ) : (
        ex && (
          <div className="stack">
            <div className="list__split">
              <span className="muted">{ex.execution_id}</span>
              <Badge tone={EXEC_TONES[ex.status]}>{ex.status}</Badge>
            </div>
            <ProgressBar completed={ex.completed_items} total={ex.total_items} label="Item terkirim" />
            {ex.failed_items > 0 && <Alert>{ex.failed_items} item gagal dikirim.</Alert>}
            <dl className="dl">
              <dt>Mulai</dt>
              <dd>{formatDateTime(ex.started_at)}</dd>
              <dt>Selesai</dt>
              <dd>{formatDateTime(ex.finished_at)}</dd>
            </dl>
            {running && (
              <button
                type="button"
                className="btn btn--danger-ghost"
                disabled={cancel.pending}
                onClick={() => cancel.run().then(refresh).catch(() => {})}
              >
                Batalkan eksekusi
              </button>
            )}
          </div>
        )
      )}

      <Modal
        open={confirming}
        title="Kirim ke Moodle?"
        onClose={() => setConfirming(false)}
        footer={
          <>
            <button type="button" className="btn btn--ghost" onClick={() => setConfirming(false)}>
              Batal
            </button>
            <button
              type="button"
              className="btn btn--primary"
              disabled={execute.pending}
              onClick={() => {
                setConfirming(false);
                execute.run().then(refresh).catch(() => {});
              }}
            >
              Ya, kirim
            </button>
          </>
        }
      >
        <p>Konten yang sudah disetujui akan dibuat di Moodle LMS ITK. Mahasiswa yang terdaftar dapat melihatnya.</p>
      </Modal>
    </Card>
  );
}

function VerificationCard() {
  const { course, version, refresh } = useCourse();
  const verificationId = course.latest_verification_id;
  const verification = useApi(
    () => (verificationId ? getVerification(course.id, verificationId) : null),
    [course.id, verificationId, version],
  );
  const start = useAction(() => startVerification(course.id));
  const v = verification.data;
  const canStart = ['EXECUTED', 'COMPLETED'].includes(course.status);

  return (
    <Card
      title="Verifikasi"
      actions={
        course.status === 'COMPLETED' && (
          <a className="btn btn--primary btn--sm" href={moodleCourseUrl(course.moodle_course_id)} target="_blank" rel="noreferrer">
            Buka di Moodle ↗
          </a>
        )
      }
    >
      <ErrorAlert error={start.error || verification.error} onClose={start.clearError} />

      {!v && !canStart && <p className="muted">Verifikasi tersedia setelah eksekusi ke Moodle selesai.</p>}
      {canStart && (
        <div className="next-step">
          <p>Periksa apakah course, section, dan aktivitas benar-benar ada dan dapat diakses mahasiswa.</p>
          <button type="button" className="btn" disabled={start.pending} onClick={() => start.run().then(refresh).catch(() => {})}>
            {v ? 'Verifikasi ulang' : 'Mulai verifikasi'}
          </button>
        </div>
      )}

      {v && (
        <div className="stack">
          <div className="list__split">
            <span className="muted">{v.verification_id}</span>
            <Badge tone={v.result === 'passed' ? 'success' : v.result === 'failed' ? 'danger' : 'info'}>
              {v.result ?? v.status}
            </Badge>
          </div>
          <ul className="checklist">
            {v.checks.map((c) => (
              <li key={c.name} className={`checklist__item checklist__item--${c.status}`}>
                <span aria-hidden="true">{c.status === 'passed' ? '✓' : '✕'}</span>
                {c.label ?? c.name}
              </li>
            ))}
            {v.status === 'running' && (
              <li className="checklist__item">
                <Spinner label="Memeriksa…" />
              </li>
            )}
          </ul>
        </div>
      )}
    </Card>
  );
}
