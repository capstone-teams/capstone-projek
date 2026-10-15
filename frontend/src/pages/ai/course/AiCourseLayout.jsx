import { useCallback, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { findCourseByMoodleId, getMonitoring } from '../../../services/courseService';
import { useApi } from '../../../hooks/useApi';
import { useCourseEvents } from '../../../hooks/useCourseEvents';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { ErrorAlert, Spinner, StatusBadge } from '../../../components/ui';
import WorkflowStepper from '../../../components/ai/WorkflowStepper';
import AiProjectStart from '../../../components/ai/course/AiProjectStart';
import { ForbiddenPage } from '../../StatusPage';

const TABS = [
  { to: '', label: 'Ringkasan', end: true },
  { to: 'rps', label: 'RPS' },
  { to: 'plan', label: 'Rencana' },
  { to: 'content', label: 'Konten' },
  { to: 'review', label: 'Review' },
  { to: 'publish', label: 'Publikasi' },
];

/**
 * Tab "Generator AI" di halaman kursus Moodle. Satu kursus memiliki satu project generator;
 * bila belum ada, tampilkan form untuk memulainya.
 * Sesuai design-api.md §17: ambil initial state via HTTP dulu, baru pakai event stream.
 */
export default function AiCourseLayout() {
  const { course: moodleCourse, isTeacher } = useMoodleCourse();
  const [events, setEvents] = useState([]);
  // Naik setiap ada event; halaman anak memakainya sebagai dependency untuk reload.
  const [version, setVersion] = useState(0);

  const { data: course, error, loading, reload } = useApi(async () => {
    const project = await findCourseByMoodleId(moodleCourse.id);
    if (!project) return null;
    const monitoring = await getMonitoring(project.id);
    setEvents(monitoring.recent_events ?? []);
    return project;
  }, [moodleCourse.id]);

  const onEvent = useCallback(
    (ev) => {
      setEvents((list) => [...list.slice(-199), ev]);
      setVersion((v) => v + 1);
      reload({ silent: true });
    },
    [reload],
  );
  useCourseEvents(course?.id, onEvent, !!course);

  const refresh = useCallback(() => {
    setVersion((v) => v + 1);
    return reload({ silent: true });
  }, [reload]);

  if (!isTeacher) return <ForbiddenPage />;
  if (loading && !course) return <Spinner />;
  if (error && !course) return <ErrorAlert error={error} />;
  if (!course) return <AiProjectStart moodleCourse={moodleCourse} onCreated={() => reload()} />;

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-muted">
          Generator konten AI · RPS {course.code} — {course.name}
        </p>
        <StatusBadge status={course.status} />
      </div>
      <WorkflowStepper status={course.status} />

      <nav className="tabs" aria-label="Bagian generator AI">
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
