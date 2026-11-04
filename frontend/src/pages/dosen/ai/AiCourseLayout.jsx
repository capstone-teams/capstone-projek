import { useCallback, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { findCourseByMoodleId } from '../../../services/courseService';
import { useApi } from '../../../hooks/useApi';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useWorkflow } from '../../../hooks/useWorkflow';
import { ErrorAlert, ErrorBoundary, Spinner, StatusBadge } from '../../../components/ui';
import WorkflowStepper from '../../../components/ai/WorkflowStepper';
import AiProjectStart from '../../../components/ai/course/AiProjectStart';
import { ForbiddenPage } from '../../StatusPage';

const TABS = [
  { to: '', label: 'Ringkasan', end: true },
  { to: 'rps', label: 'RPS' },
  { to: 'target', label: 'Course Target' },
  { to: 'plan', label: 'Rencana' },
  { to: 'content', label: 'Konten' },
  { to: 'review', label: 'Review' },
  { to: 'publish', label: 'Publikasi' },
];

/**
 * Layout tab Generator AI pada kursus Moodle.
 */
export default function AiCourseLayout() {
  const moodleContext = useMoodleCourse();
  const moodleCourse = moodleContext?.course;
  const isTeacher = moodleContext?.isTeacher;
  const [version, setVersion] = useState(0);

  const { data: course, error, loading, reload } = useApi(async () => {
    if (!moodleCourse?.id) return null;
    return findCourseByMoodleId(moodleCourse.id);
  }, [moodleCourse?.id]);

  const {
    workflowId,
    workflow,
    events,
    reload: reloadWorkflow,
  } = useWorkflow(course);

  const refresh = useCallback(() => {
    setVersion((v) => v + 1);
    reloadWorkflow();
    return reload({ silent: true });
  }, [reload, reloadWorkflow]);

  if (!isTeacher) return <ForbiddenPage />;
  if (loading && !course) return <Spinner />;
  if (error && !course) return <ErrorAlert error={error} />;
  if (!course) return <AiProjectStart moodleCourse={moodleCourse} onCreated={() => reload()} />;

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-muted">
          Generator konten AI · RPS {course.code ?? course.shortname} — {course.name ?? course.fullname}
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

      <ErrorBoundary>
        <Outlet context={{ course, workflow, workflowId, events, version, refresh }} />
      </ErrorBoundary>
    </>
  );
}
