import { useCallback, useState } from 'react';
import { NavLink, Outlet, useLocation, useSearchParams } from 'react-router-dom';
import { findCourseByMoodleId } from '../../../services/courseService';
import { useApi } from '../../../hooks/useApi';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useWorkflowMonitor } from '../../../hooks/useWorkflowMonitor';
import { getRps } from '../../../services/rpsService';
import { findWorkflowForCourse } from '../../../services/workflowService';
import { COURSE_API_AVAILABLE } from '../../../services/config';
import { ErrorAlert, ErrorBoundary, Spinner, StatusBadge } from '../../../components/ui';
import WorkflowStepper from '../../../components/ai/WorkflowStepper';
import { ForbiddenPage } from '../../StatusPage';
import WorkflowLayout from './WorkflowLayout';

export const TABS = [
  { to: '', label: 'Ringkasan', end: true },
  { to: 'rps', label: 'RPS' },
  { to: 'plan', label: 'Rencana' },
  { to: 'content', label: 'Konten' },
  { to: 'review', label: 'Review' },
  { to: 'publish', label: 'Publikasi' },
  // Pemantauan workflow (FE-10) di akhir agar urutan tab project kursus tetap rapi.
  { to: 'workflows', label: 'Workflow' },
];

/**
 * Tab "Generator AI" di halaman kursus. Selalu menampilkan layout utama (stepper + tab).
 * Sesuai design-api.md §17: ambil initial state via HTTP dulu, baru pakai event stream.
 */
function CourseProjectLayout() {
  const { course: moodleCourse, isTeacher } = useMoodleCourse();
  // Status workflow dapat dibuka walau kursus ini belum punya project, mis. dari tautan di daftar RPS.
  const onStatusPage = useLocation().pathname.endsWith('/workflows');
  // Naik setiap ada event; halaman anak memakainya sebagai dependency untuk reload.
  const [version, setVersion] = useState(0);

  const { data: dbCourse, error, loading, reload } = useApi(async () => {
    if (!moodleCourse?.id) return null;
    return findCourseByMoodleId(moodleCourse.id);
  }, [moodleCourse?.id]);

  // ?rps=<id>: hasil analisis RPS dari daftar RPS, walau kursus ini belum punya project.
  const [params] = useSearchParams();
  const rpsParam = params.get('rps');
  const workflowParam = params.get('workflow');

  // Cari workflow yang menargetkan kursus Moodle ini (FE-10 / FE-11)
  const activeWfQuery = useApi(
    () => (moodleCourse?.id ? findWorkflowForCourse(moodleCourse.id).catch(() => null) : null),
    [moodleCourse?.id, version]
  );
  const activeWorkflow = activeWfQuery.data;

  // Baca session storage untuk rps / workflow yang baru diunggah di kursus ini
  const sessionRpsId = moodleCourse?.id ? sessionStorage.getItem(`agentic-lms.course-rps.${moodleCourse.id}`) : null;
  const sessionWorkflowId = moodleCourse?.id ? sessionStorage.getItem(`agentic-lms.course-workflow.${moodleCourse.id}`) : null;

  // Fallback course dari data Moodle jika belum tercatat di database internal
  const baseCourse = dbCourse ?? (moodleCourse ? {
    id: moodleCourse.id,
    moodle_course_id: moodleCourse.id,
    shortname: moodleCourse.shortname,
    fullname: moodleCourse.fullname,
    name: moodleCourse.fullname,
    code: moodleCourse.shortname,
    status: 'DRAFT',
  } : null);

  const effectiveWorkflowId = workflowParam
    ?? activeWorkflow?.id
    ?? sessionWorkflowId
    ?? baseCourse?.workflow_id
    ?? null;

  // Workflow project: dari project bila ada, atau dari RPS-nya (GET /rps/{id}); dipantau real-time (FE-10.2).
  const projectRps = useApi(
    () => (!effectiveWorkflowId && (rpsParam || sessionRpsId || baseCourse?.rps_id) ? getRps(rpsParam || sessionRpsId || baseCourse.rps_id).catch(() => null) : null),
    [effectiveWorkflowId, rpsParam, sessionRpsId, baseCourse?.rps_id],
  );

  const workflowId = effectiveWorkflowId ?? projectRps.data?.workflow_id ?? null;

  const effectiveRpsId = rpsParam
    ?? activeWorkflow?.rps_id
    ?? sessionRpsId
    ?? projectRps.data?.id
    ?? baseCourse?.rps_id
    ?? null;

  const course = baseCourse ? {
    ...baseCourse,
    rps_id: effectiveRpsId,
    workflow_id: workflowId,
  } : null;

  const monitor = useWorkflowMonitor(workflowId);
  const { reload: reloadWorkflow, workflow, events } = monitor;

  const refresh = useCallback(() => {
    setVersion((v) => v + 1);
    reloadWorkflow();
    activeWfQuery.reload({ silent: true });
    return reload({ silent: true });
  }, [reload, reloadWorkflow, activeWfQuery]);

  if (!isTeacher) return <ForbiddenPage />;
  if (loading && !course) return <Spinner />;
  if (error && !course) return <ErrorAlert error={error} />;
  if (!course && onStatusPage) return <Outlet context={{ course: null, events: [], version, refresh }} />;

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
        <Outlet context={{
          course,
          moodleCourse,
          workflow: workflow ?? activeWorkflow,
          workflowId,
          events,
          connection: monitor.connection,
          version,
          refresh,
          initialRpsId: dbCourse?.rps_id ?? null,
        }} />
      </ErrorBoundary>
    </>
  );
}

export default function AiCourseLayout() {
  return COURSE_API_AVAILABLE ? <CourseProjectLayout /> : <WorkflowLayout />;
}
