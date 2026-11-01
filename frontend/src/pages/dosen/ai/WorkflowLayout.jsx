import { useCallback, useState } from 'react';
import { NavLink, Outlet, useSearchParams } from 'react-router-dom';
import { findWorkflowForCourse } from '../../../services/workflowService';
import { useApi } from '../../../hooks/useApi';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useWorkflowEvents } from '../../../hooks/useWorkflowEvents';
import { ErrorAlert, Spinner } from '../../../components/ui';
import AiProjectStart from '../../../components/ai/course/AiProjectStart';
import { ForbiddenPage } from '../../StatusPage';

const TABS = [
  { to: '', label: 'Ringkasan', end: true },
  { to: 'rps', label: 'RPS' },
];

/**
 * Generator AI pada backend nyata: project kursus adalah workflow RPS yang course target-nya
 * (moodle_course_id) menunjuk kursus ini. Tahap setelah analisis RPS belum punya API.
 */
export default function WorkflowLayout() {
  const { course: moodleCourse, isTeacher } = useMoodleCourse();
  const { data: workflow, error, loading, reload } = useApi(() => findWorkflowForCourse(moodleCourse.id), [moodleCourse.id]);
  const [version, setVersion] = useState(0);
  // ?rps=<id>: hasil analisis RPS yang belum punya workflow (mis. data seed), tanpa project kursus.
  const [params] = useSearchParams();
  const rpsId = params.get('rps');

  const refresh = useCallback(() => {
    setVersion((v) => v + 1);
    return reload({ silent: true });
  }, [reload]);
  useWorkflowEvents([workflow?.id], refresh);

  if (!isTeacher) return <ForbiddenPage />;
  if (loading && !workflow) return <Spinner />;
  if (error && !workflow) return <ErrorAlert error={error} />;
  if (!workflow && rpsId) return <Outlet context={{ course: { rps_id: rpsId }, events: [], version, refresh }} />;
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
      <Outlet context={{ course: workflow, events: [], version, refresh }} />
    </>
  );
}
