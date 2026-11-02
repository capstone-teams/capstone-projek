import { useCallback, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { findCourseByMoodleId, getMonitoring } from '../../../services/courseService';
import { useApi } from '../../../hooks/useApi';
import { useCourseEvents } from '../../../hooks/useCourseEvents';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { COURSE_API_AVAILABLE } from '../../../services/config';
import { ErrorAlert, Spinner, StatusBadge } from '../../../components/ui';
import WorkflowStepper from '../../../components/ai/WorkflowStepper';
import AiProjectStart from '../../../components/ai/course/AiProjectStart';
import { ForbiddenPage } from '../../StatusPage';
import WorkflowLayout from './WorkflowLayout';

const TABS = [
  { to: '', label: 'Ringkasan', end: true },
  { to: 'rps', label: 'RPS' },
  { to: 'workflows', label: 'Workflow' },
  { to: 'plan', label: 'Rencana' },
  { to: 'content', label: 'Konten' },
  { to: 'review', label: 'Review' },
  { to: 'publish', label: 'Publikasi' },
];

/**
 * Tab "Generator AI" di halaman kursus. Satu kursus memiliki satu project generator;
 * bila belum ada, tampilkan form untuk memulainya.
 * Sesuai design-api.md §17: ambil initial state via HTTP dulu, baru pakai event stream.
 */
function CourseProjectLayout() {
  const { course: moodleCourse, isTeacher } = useMoodleCourse();
  const [events, setEvents] = useState([]);
  // Status workflow dapat dibuka walau kursus ini belum punya project, mis. dari tautan di daftar RPS.
  const onStatusPage = useLocation().pathname.endsWith('/workflows');
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
  if (!course && onStatusPage) return <Outlet context={{ course: null, events: [], version, refresh }} />;
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

export default function AiCourseLayout() {
  return COURSE_API_AVAILABLE ? <CourseProjectLayout /> : <WorkflowLayout />;
}
