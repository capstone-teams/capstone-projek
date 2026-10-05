import { Link } from 'react-router-dom';
import { listCourses } from '../../services/courseService';
import { useApi } from '../../hooks/useApi';
import { usePolling } from '../../hooks/usePolling';
import { Card, EmptyState, ErrorAlert, PageHeader, ProgressBar, Spinner, StatusBadge } from '../../components/ui';
import { isBusy } from '../../utils/workflow';
import { formatDateTime } from '../../utils/format';

export default function AiDashboardPage() {
  const { data, error, loading, reload } = useApi(listCourses);
  const courses = data?.courses ?? [];
  const anyBusy = courses.some((c) => isBusy(c.status));

  usePolling(() => reload({ silent: true }), 3000, anyBusy);

  const count = (pred) => courses.filter(pred).length;
  const stats = [
    { label: 'Total course', value: courses.length },
    { label: 'Sedang diproses', value: count((c) => isBusy(c.status)) },
    { label: 'Menunggu review', value: count((c) => c.status.startsWith('WAITING')) },
    { label: 'Selesai', value: count((c) => c.status === 'COMPLETED') },
  ];

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Pantau generation project course Moodle Anda."
        actions={
          <Link to="/ai/courses/new" className="btn btn--primary">
            + Course baru
          </Link>
        }
      />

      <ErrorAlert error={error} />

      <div className="stats">
        {stats.map((s) => (
          <div key={s.label} className="stat">
            <span className="stat__value">{loading && !data ? '–' : s.value}</span>
            <span className="stat__label">{s.label}</span>
          </div>
        ))}
      </div>

      <Card title="Generation project">
        {loading && !data ? (
          <Spinner />
        ) : courses.length === 0 ? (
          <EmptyState
            title="Belum ada course."
            action={
              <Link to="/ai/courses/new" className="btn btn--primary">
                Buat course pertama
              </Link>
            }
          >
            Unggah RPS lalu buat generation project untuk mulai.
          </EmptyState>
        ) : (
          <ul className="course-list">
            {courses.map((c) => (
              <li key={c.id}>
                <Link to={`/ai/courses/${c.id}`} className="course-row">
                  <div className="course-row__main">
                    <strong>
                      {c.code} — {c.name}
                    </strong>
                    <span className="muted">
                      Moodle: {c.moodle_course_id || 'belum dipilih'} · Diperbarui {formatDateTime(c.updated_at)}
                    </span>
                    {isBusy(c.status) && c.progress && (
                      <ProgressBar completed={c.progress.completed} total={c.progress.total} label={c.stage ?? ''} />
                    )}
                  </div>
                  <StatusBadge status={c.status} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
