import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { approveContent, getReview, rejectContent, validateContent } from '../../../services/courseService';
import { useAction, useApi } from '../../../hooks/useApi';
import { Alert, Badge, Card, EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import InstructionModal from '../../../components/InstructionModal';
import { formatDateTime } from '../../../utils/format';

const SEVERITY_TONES = { high: 'danger', medium: 'warning', low: 'neutral' };
const REVIEWABLE = ['WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED'];

export default function CourseReviewPage() {
  const { course, version, refresh } = useCourse();
  const review = useApi(() => getReview(course.id), [course.id, version]);
  const validate = useAction(() => validateContent(course.id));
  const approve = useAction(() => approveContent(course.id));
  const [rejecting, setRejecting] = useState(false);

  const data = review.data;
  const items = data?.items ?? [];
  const issues = items.flatMap((i) => i.issues);
  const blocking = issues.some((i) => i.severity === 'high');
  const waiting = course.status === 'WAITING_CONTENT_REVIEW';

  if (review.loading && !data) return <Spinner />;
  if (!items.length) {
    return (
      <Card>
        <ErrorAlert error={review.error} />
        <EmptyState title="Belum ada konten untuk direview.">Konten akan muncul di sini setelah selesai digenerate dan divalidasi.</EmptyState>
      </Card>
    );
  }

  return (
    <div className="stack">
      <Card
        title="Hasil validasi"
        actions={
          <>
            {data.validation_result && (
              <Badge tone={data.validation_result === 'passed' ? 'success' : 'warning'}>
                {data.validation_result === 'passed' ? 'Lolos' : 'Ada temuan'}
              </Badge>
            )}
            {REVIEWABLE.includes(course.status) && (
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={validate.pending}
                onClick={() => validate.run().then(refresh).catch(() => {})}
              >
                {validate.pending ? 'Memvalidasi…' : 'Validasi ulang'}
              </button>
            )}
          </>
        }
      >
        <ErrorAlert error={validate.error} onClose={validate.clearError} />
        {issues.length === 0 ? (
          <p className="muted">Tidak ada temuan. Konten konsisten dengan RPS dan struktur yang diharapkan.</p>
        ) : (
          <ul className="issues">
            {issues.map((issue, i) => (
              <li key={i}>
                <Badge tone={SEVERITY_TONES[issue.severity]}>{issue.severity}</Badge>
                <span>{issue.message}</span>
                {issue.week && (
                  <Link to={`../content?week=${issue.week}`} relative="path" className="btn btn--ghost btn--sm">
                    Lihat minggu {issue.week}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card
        title="Review konten"
        actions={
          waiting && (
            <>
              <button type="button" className="btn btn--danger-ghost" onClick={() => setRejecting(true)}>
                Tolak
              </button>
              <button
                type="button"
                className="btn btn--primary"
                disabled={approve.pending || blocking}
                title={blocking ? 'Selesaikan temuan tingkat high terlebih dahulu' : undefined}
                onClick={() => approve.run().then(refresh).catch(() => {})}
              >
                {approve.pending ? 'Menyimpan…' : 'Setujui semua konten'}
              </button>
            </>
          )
        }
      >
        <ErrorAlert error={approve.error || review.error} onClose={approve.clearError} />
        {waiting && issues.length > 0 && !blocking && (
          <Alert tone="warning">Masih ada temuan validasi. Anda tetap dapat menyetujui, atau regenerasi minggu terkait.</Alert>
        )}
        {!REVIEWABLE.includes(course.status) && <Alert tone="info">Review sudah selesai untuk tahap ini.</Alert>}

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Minggu</th>
                <th>Topik</th>
                <th>Materi</th>
                <th>Tugas</th>
                <th>Kuis</th>
                <th>Temuan</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.content_id}>
                  <td>{it.week}</td>
                  <td>
                    <Link to={`../content?week=${it.week}`} relative="path">
                      {it.topic}
                    </Link>
                    {it.revision > 0 && <small className="muted"> · revisi {it.revision}</small>}
                  </td>
                  <td>{it.material_count}</td>
                  <td>{it.has_assignment ? '✓' : '–'}</td>
                  <td>{it.has_quiz ? '✓' : '–'}</td>
                  <td>
                    {it.issues.length ? <Badge tone={SEVERITY_TONES[it.issues[0].severity]}>{it.issues.length}</Badge> : '–'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {data.rejections?.length > 0 && (
        <Card title="Riwayat penolakan">
          <ul className="list">
            {data.rejections.map((r) => (
              <li key={r.rejected_at} className="list__split">
                <span>{r.reason}</span>
                <small className="muted">{formatDateTime(r.rejected_at)}</small>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <InstructionModal
        open={rejecting}
        title="Tolak konten"
        label="Alasan penolakan"
        placeholder="Contoh: Materi minggu 4 tidak sesuai dengan RPS."
        submitLabel="Tolak konten"
        danger
        onClose={() => setRejecting(false)}
        onSubmit={(reason) => rejectContent(course.id, reason).then(refresh)}
      />
    </div>
  );
}
