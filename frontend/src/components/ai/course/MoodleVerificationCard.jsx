import { useCourse } from '../../../hooks/useCourse';
import { getVerification, startVerification } from '../../../services/courseService';
import { MOODLE_URL } from '../../../services/config';
import { useAction, useApi } from '../../../hooks/useApi';
import { Badge, Card, ErrorAlert, Spinner } from '../../ui';

function moodleCourseUrl(id) {
  if (!id) return MOODLE_URL;
  return /^\d+$/.test(id)
    ? `${MOODLE_URL}/course/view.php?id=${id}`
    : `${MOODLE_URL}/course/search.php?search=${encodeURIComponent(id)}`;
}

export default function MoodleVerificationCard() {
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
