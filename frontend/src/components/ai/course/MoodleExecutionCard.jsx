import { useState } from 'react';
import { useCourse } from '../../../hooks/useCourse';
import { cancelExecution, executeCourse, getExecution } from '../../../services/courseService';
import { useAction, useApi } from '../../../hooks/useApi';
import { usePolling } from '../../../hooks/usePolling';
import { Alert, Badge, Card, ErrorAlert, Modal, ProgressBar, Spinner } from '../../ui';
import { formatDateTime } from '../../../utils/format';

const EXEC_TONES = { completed: 'success', failed: 'danger', cancelled: 'neutral', queued: 'info', running: 'info' };

export default function MoodleExecutionCard() {
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
