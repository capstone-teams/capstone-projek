import { useCallback, useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { findCourseByMoodleId } from '../../../services/courseService';
import { useApi } from '../../../hooks/useApi';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useWorkflowMonitor } from '../../../hooks/useWorkflowMonitor';
import { getRps } from '../../../services/rpsService';
import {
  findWorkflowForCourse,
  getActiveCourseBinding,
  moodleCourseIdOf,
  saveActiveCourseBinding,
} from '../../../services/workflowService';
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
  const { course: moodleCourse, isTeacher } = useMoodleCourse() ?? {};
  const params = useParams();
  const courseIdParam = params.courseId;
  const moodleId = moodleCourseIdOf(moodleCourse) || (Number.isInteger(Number(courseIdParam)) && Number(courseIdParam) > 0 ? Number(courseIdParam) : null);
  const courseLookupKey = moodleId || courseIdParam;

  // Status workflow dapat dibuka walau kursus ini belum punya project, mis. dari tautan di daftar RPS.
  const onStatusPage = useLocation().pathname.endsWith('/workflows');
  // Naik setiap ada event; halaman anak memakainya sebagai dependency untuk reload.
  const [version, setVersion] = useState(0);

  const { data: dbCourse, error, loading, reload } = useApi(async () => {
    if (!courseLookupKey) return null;
    return findCourseByMoodleId(courseLookupKey);
  }, [courseLookupKey]);

  // ?rps=<id>: hasil analisis RPS dari daftar RPS, walau kursus ini belum punya project.
  const [searchParams] = useSearchParams();
  const rpsParam = searchParams.get('rps');
  const workflowParam = searchParams.get('workflow');

  // Kumpulkan seluruh alias identifier yang mungkin milik kursus ini (angka, string ID, shortname)
  const courseKeys = [moodleId, courseIdParam, dbCourse?.id, dbCourse?.shortname, moodleCourse?.id, moodleCourse?.shortname].filter(Boolean);
  const courseKeysKey = courseKeys.join(',');

  // Binding aktif kursus ini yang tersimpan (FE-10 / RPS overwrite persistence)
  const activeBinding = getActiveCourseBinding(...courseKeys);

  // Cari workflow yang menargetkan kursus Moodle ini (FE-10 / FE-11)
  const activeWfQuery = useApi(
    () => (courseKeys.length ? findWorkflowForCourse(...courseKeys).catch(() => null) : null),
    [courseKeysKey, version]
  );
  const activeWorkflow = activeWfQuery.data;

  // Sinkronkan ke storage lokal HANYA jika belum ada binding lokal atau workflowId-nya cocok
  useEffect(() => {
    if (courseKeys.length && activeWorkflow?.id) {
      if (!activeBinding?.rpsId || activeBinding.workflowId === activeWorkflow.id) {
        saveActiveCourseBinding(moodleId || courseIdParam, {
          workflowId: activeWorkflow.id,
          rpsId: activeWorkflow.rps_id,
        }, courseKeys);
      }
    }
  }, [moodleId, courseIdParam, activeWorkflow?.id, activeWorkflow?.rps_id, activeBinding?.rpsId, activeBinding?.workflowId, courseKeysKey]);

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
    ?? activeBinding?.workflowId
    ?? activeWorkflow?.id
    ?? baseCourse?.workflow_id
    ?? null;

  // Workflow project: dari project bila ada, atau dari RPS-nya (GET /rps/{id}); dipantau real-time (FE-10.2).
  const projectRps = useApi(
    () => (!effectiveWorkflowId && (rpsParam || (!activeBinding?.rpsId && baseCourse?.rps_id))
      ? getRps(rpsParam || baseCourse.rps_id).catch(() => null)
      : null),
    [effectiveWorkflowId, rpsParam, activeBinding?.rpsId, baseCourse?.rps_id],
  );

  const workflowId = effectiveWorkflowId ?? projectRps.data?.workflow_id ?? null;

  const effectiveRpsId = rpsParam
    ?? activeBinding?.rpsId
    ?? activeWorkflow?.rps_id
    ?? projectRps.data?.id
    ?? (!activeBinding?.rpsId ? baseCourse?.rps_id : null)
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
  }, [reload, reloadWorkflow, activeWfQuery, setVersion]);

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
