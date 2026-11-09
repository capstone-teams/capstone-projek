import { useCallback, useState } from 'react';
import { NavLink, Outlet, useSearchParams } from 'react-router-dom';
import { findCourseByMoodleId } from '../../../services/courseService';
import { findWorkflowForCourse, moodleCourseIdOf } from '../../../services/workflowService';
import { useApi } from '../../../hooks/useApi';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useWorkflowMonitor } from '../../../hooks/useWorkflowMonitor';
import { getRps } from '../../../services/rpsService';
import { COURSE_ACTIONS_AVAILABLE, COURSE_API_AVAILABLE } from '../../../services/config';
import { ErrorAlert, ErrorBoundary, Spinner, StatusBadge } from '../../../components/ui';
import WorkflowStepper from '../../../components/ai/WorkflowStepper';
import WorkflowStatusBadge from '../../../components/ai/WorkflowStatusBadge';
import AiProjectStart from '../../../components/ai/course/AiProjectStart';
import { ForbiddenPage } from '../../StatusPage';
import WorkflowLayout from './WorkflowLayout';

const TABS = [
  { to: '', label: 'Ringkasan', end: true },
  { to: 'rps', label: 'RPS' },
  { to: 'target', label: 'Course Target' },
  { to: 'plan', label: 'Rencana' },
  { to: 'content', label: 'Konten' },
  { to: 'review', label: 'Review' },
  { to: 'publish', label: 'Publikasi' },
  // Pemantauan workflow (FE-10) di akhir agar urutan tab project kursus tetap seperti FE-09.
  { to: 'workflows', label: 'Workflow' },
];

// RPS yang terakhir dipilih atau diunggah untuk kursus ini, per browser. Hanya kemudahan sampai workflow-nya
// diberi course target kursus ini (PUT /workflows/{id}/moodle-target), yang menjadi sumber resmi.
const rpsKey = (moodleId) => `agentic-lms.ai-course-rps.${moodleId}`;
function readCourseRps(moodleId) {
  try {
    return moodleId ? localStorage.getItem(rpsKey(moodleId)) : null;
  } catch {
    return null;
  }
}
function writeCourseRps(moodleId, rpsId) {
  try {
    if (rpsId) localStorage.setItem(rpsKey(moodleId), rpsId);
    else localStorage.removeItem(rpsKey(moodleId));
  } catch {
    // Penyimpanan browser tidak tersedia: pilihan hanya berlaku selama halaman terbuka.
  }
}

/**
 * Workflow kursus tanpa project /courses: workflow yang course target-nya kursus ini, atau workflow RPS yang
 * terakhir dipilih untuk kursus ini. { workflowId, rpsId } bernilai null bila belum ada.
 */
async function resolveCourseWorkflow(moodleId, storedRpsId) {
  const targeted = await findWorkflowForCourse(moodleId).catch(() => null);
  if (targeted) return { workflowId: targeted.id, rpsId: targeted.rps_id ?? null };
  const rps = storedRpsId ? await getRps(storedRpsId).catch(() => null) : null;
  return { workflowId: rps?.workflow_id ?? null, rpsId: rps?.id ?? null };
}

/**
 * Tab "Generator AI" di halaman kursus, dengan tab yang sama untuk setiap kursus. Kursus yang punya project
 * generator (/courses) memakai project itu. Tanpa project, alur mengikuti workflow backend (DL-011): workflow
 * yang menargetkan kursus ini atau RPS yang dipilih untuk kursus ini. Membuat project hanya ada di mode mock,
 * sehingga hanya di sana formulir "Mulai generator AI" ditampilkan.
 * Sesuai design-api.md §17: ambil initial state via HTTP dulu, baru pakai event stream.
 */
function CourseProjectLayout() {
  const { course: moodleCourse, isTeacher } = useMoodleCourse();
  const moodleId = moodleCourseIdOf(moodleCourse);
  // Naik setiap ada event; halaman anak memakainya sebagai dependency untuk reload.
  const [version, setVersion] = useState(0);

  const { data: course, error, loading, reload } = useApi(async () => {
    if (!moodleCourse?.id) return null;
    return findCourseByMoodleId(moodleCourse.id);
  }, [moodleCourse?.id]);

  // ?rps=<id>: hasil analisis RPS dari daftar RPS.
  const [params] = useSearchParams();
  const rpsParam = params.get('rps');

  // Workflow project: dari project bila ada, atau dari RPS-nya (GET /rps/{id}); dipantau real-time (FE-10.2).
  const projectRps = useApi(
    () => (course?.rps_id && !course?.workflow_id ? getRps(course.rps_id) : null),
    [course?.rps_id, course?.workflow_id],
  );
  // Tanpa project (backend nyata): workflow kursus dicari dari course target atau RPS pilihan kursus ini.
  const workflowMode = !COURSE_ACTIONS_AVAILABLE && !loading && !error && !course;
  const [storedRps, setStoredRps] = useState(() => readCourseRps(moodleId));
  const linked = useApi(
    () => (workflowMode && moodleId ? resolveCourseWorkflow(moodleId, storedRps) : null),
    [workflowMode, moodleId, storedRps, version],
  );
  const workflowId = course?.workflow_id ?? projectRps.data?.workflow_id ?? linked.data?.workflowId ?? null;
  const monitor = useWorkflowMonitor(workflowId);
  const { reload: reloadWorkflow, workflow, events } = monitor;

  const refresh = useCallback(() => {
    setVersion((v) => v + 1);
    reloadWorkflow();
    return reload({ silent: true });
  }, [reload, reloadWorkflow]);
  /** Pakai RPS ini untuk kursus ini (mis. setelah diunggah dari tab Generator AI kursus). */
  const selectRps = useCallback((rpsId) => {
    writeCourseRps(moodleId, rpsId);
    setStoredRps(rpsId);
  }, [moodleId]);

  if (!isTeacher) return <ForbiddenPage />;
  if (loading && !course) return <Spinner />;
  if (error && !course) return <ErrorAlert error={error} />;
  if (!course && !workflowMode) return <AiProjectStart moodleCourse={moodleCourse} onCreated={() => reload()} />;
  if (workflowMode && linked.loading && !linked.data) return <Spinner />;

  // Konteks tab: project kursus, atau ringkasan kursus Moodle dan workflow-nya (tanpa `id` project).
  const context = course ?? {
    moodle_course_id: moodleId,
    fullname: moodleCourse.fullname,
    shortname: moodleCourse.shortname,
    name: moodleCourse.fullname,
    code: moodleCourse.shortname,
    rps_id: rpsParam ?? linked.data?.rpsId ?? null,
    workflow_id: workflowId,
    status: null,
  };

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-muted">
          Generator konten AI · RPS {context.code ?? context.shortname} — {context.name ?? context.fullname}
        </p>
        {course ? <StatusBadge status={course.status} /> : workflow && <WorkflowStatusBadge workflow={workflow} />}
      </div>
      {course && <WorkflowStepper status={course.status} />}

      <nav className="tabs" aria-label="Bagian generator AI">
        {TABS.map((t) => (
          <NavLink key={t.label} to={t.to} end={t.end} className="tabs__link">
            {t.label}
          </NavLink>
        ))}
      </nav>

      <ErrorBoundary>
        <Outlet context={{ course: context, workflow, workflowId, events, connection: monitor.connection, version, refresh, selectRps }} />
      </ErrorBoundary>
    </>
  );
}

export default function AiCourseLayout() {
  const { course } = useMoodleCourse();
  // Dipasang ulang per kursus agar pilihan RPS kursus sebelumnya tidak terbawa.
  return COURSE_API_AVAILABLE ? <CourseProjectLayout key={course?.id} /> : <WorkflowLayout />;
}
