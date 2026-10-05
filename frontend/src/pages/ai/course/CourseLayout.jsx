import { useCallback, useState } from 'react';
import { NavLink, Outlet, useParams } from 'react-router-dom';
import { getCourse, getMonitoring } from '../../../services/courseService';
import { useApi } from '../../../hooks/useApi';
import { useCourseEvents } from '../../../hooks/useCourseEvents';
import { ErrorAlert, PageHeader, Spinner, StatusBadge } from '../../../components/ui';
import WorkflowStepper from '../../../components/WorkflowStepper';

const TABS = [
  { to: '', label: 'Ringkasan', end: true },
  { to: 'plan', label: 'Rencana' },
  { to: 'content', label: 'Konten' },
  { to: 'review', label: 'Review' },
  { to: 'moodle', label: 'Moodle' },
];

/**
 * Memuat course, lalu mengikuti event real-time-nya.
 * Sesuai design-api.md §17: ambil initial state via HTTP dulu, baru pakai event stream.
 */
export default function CourseLayout() {
  const { courseId } = useParams();
  const [events, setEvents] = useState([]);
  // Naik setiap ada event; halaman anak memakainya sebagai dependency untuk reload.
  const [version, setVersion] = useState(0);

  const { data: course, error, loading, reload } = useApi(async () => {
    const [c, monitoring] = await Promise.all([getCourse(courseId), getMonitoring(courseId)]);
    setEvents(monitoring.recent_events ?? []);
    return c;
  }, [courseId]);

  const onEvent = useCallback(
    (ev) => {
      setEvents((list) => [...list.slice(-199), ev]);
      setVersion((v) => v + 1);
      reload({ silent: true });
    },
    [reload],
  );
  useCourseEvents(courseId, onEvent, !!course);

  const refresh = useCallback(() => {
    setVersion((v) => v + 1);
    return reload({ silent: true });
  }, [reload]);

  if (loading && !course) return <Spinner />;
  if (error && !course) return <ErrorAlert error={error} />;

  return (
    <>
      <PageHeader
        title={`${course.code} — ${course.name}`}
        subtitle={`Moodle: ${course.moodle_course_id || 'belum dipilih'} · ${course.id}`}
        actions={<StatusBadge status={course.status} />}
      />
      <WorkflowStepper status={course.status} />

      <nav className="tabs" aria-label="Bagian course">
        {TABS.map((t) => (
          <NavLink key={t.label} to={t.to} end={t.end} className="tabs__link">
            {t.label}
          </NavLink>
        ))}
      </nav>

      <Outlet context={{ course, events, version, refresh }} />
    </>
  );
}
