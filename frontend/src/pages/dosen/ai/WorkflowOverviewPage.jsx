import { useCourse } from '../../../hooks/useCourse';
import { useAction, useApi } from '../../../hooks/useApi';
import { getWorkflowEvents, setMoodleTarget } from '../../../services/workflowService';
import { Card, ErrorAlert } from '../../../components/ui';
import EventLog from '../../../components/ai/EventLog';
import WorkflowStatusPanel from '../../../components/ai/WorkflowStatusPanel';

/** Status workflow RPS kursus ini (GET /workflows/{id} dan riwayat event-nya); lihat juga tab Workflow. */
export default function WorkflowOverviewPage() {
  const { course: workflow, version, refresh } = useCourse();
  const events = useApi(() => getWorkflowEvents(workflow.id), [workflow.id, version]);
  const release = useAction(() => setMoodleTarget(workflow.id, null));

  return (
    <div className="grid grid--2">
      <Card title="Status workflow">
        <ErrorAlert error={release.error} onClose={release.clearError} />
        <WorkflowStatusPanel workflow={workflow} events={events.data ?? []} />
        <button type="button" className="btn mt-4" disabled={release.pending} onClick={() => release.run().then(refresh).catch(() => {})}>
          Lepas RPS dari kursus ini
        </button>
      </Card>
      <Card title="Aktivitas agent">
        <ErrorAlert error={events.error} />
        <EventLog events={events.data} />
      </Card>
    </div>
  );
}
