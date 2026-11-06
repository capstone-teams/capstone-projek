import { useCallback, useState } from 'react';
import { NavLink, Outlet, useLocation, useSearchParams } from 'react-router-dom';
import { findWorkflowForCourse, moodleCourseIdOf } from '../../../services/workflowService';
import { useApi } from '../../../hooks/useApi';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useWorkflowMonitor } from '../../../hooks/useWorkflowMonitor';
import { ErrorAlert, Spinner } from '../../../components/ui';
import AiProjectStart from '../../../components/ai/course/AiProjectStart';
import { ForbiddenPage } from '../../StatusPage';

const TABS = [
  { to: '', label: 'Ringkasan', end: true },
  { to: 'rps', label: 'RPS' },
  { to: 'target', label: 'Course Target' },
  { to: 'workflows', label: 'Workflow' },
];

/**
 * Generator AI pada backend nyata: project kursus adalah workflow RPS yang course target-nya
 * (moodle_course_id) menunjuk kursus ini. Tahap setelah analisis RPS belum punya API.
 */
export default function WorkflowLayout() {
  const { course: moodleCourse, isTeacher } = useMoodleCourse();
  // Workflow kursus dicari lewat nomor kursus Moodle-nya (moodle_course_id), bukan id kursus backend.
  const moodleId = moodleCourseIdOf(moodleCourse);
  const { data: workflow, error, loading, reload } = useApi(() => (moodleId ? findWorkflowForCourse(moodleId) : null), [moodleId]);
  const [version, setVersion] = useState(0);
  // ?rps=<id>: hasil analisis RPS yang belum punya workflow (mis. data seed), tanpa project kursus.
  const [params] = useSearchParams();
  const rpsId = params.get('rps');
  // Status workflow dapat dibuka walau kursus ini belum punya project, mis. dari tautan di daftar RPS.
  const onStatusPage = useLocation().pathname.endsWith('/workflows');

  const refresh = useCallback(() => {
    setVersion((v) => v + 1);
    return reload({ silent: true });
  }, [reload]);
  // Status dan event workflow kursus ini diperbarui real-time (FE-10.2) dan dibagikan ke halaman di bawahnya.
  const monitor = useWorkflowMonitor(workflow?.id);
  const live = monitor.workflow ?? workflow;

  if (!isTeacher) return <ForbiddenPage />;
  if (loading && !workflow) return <Spinner />;
  if (error && !workflow) return <ErrorAlert error={error} />;
  if (!workflow && (rpsId || onStatusPage)) return <Outlet context={{ course: { rps_id: rpsId }, events: [], connection: null, version, refresh }} />;
  if (!workflow) return <AiProjectStart moodleCourse={moodleCourse} onCreated={() => reload()} />;

  return (
    <>
      <nav className="tabs" aria-label="Bagian generator AI">
        {TABS.map((t) => (
          <NavLink key={t.label} to={t.to} end={t.end} className="tabs__link">
            {t.label}
          </NavLink>
        ))}
      </nav>
      <Outlet context={{ course: live, workflow: live, workflowId: live.id, events: monitor.events, connection: monitor.connection, version, refresh }} />
    </>
  );
}
