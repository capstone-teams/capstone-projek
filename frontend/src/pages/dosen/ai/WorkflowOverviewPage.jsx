import { useCourse } from '../../../hooks/useCourse';
import { useAction } from '../../../hooks/useApi';
import { setMoodleTarget } from '../../../services/workflowService';
import { Card, ErrorAlert } from '../../../components/ui';
import EventLog from '../../../components/ai/EventLog';
import WorkflowConnectionNote from '../../../components/ai/WorkflowConnectionNote';
import WorkflowStatusPanel from '../../../components/ai/WorkflowStatusPanel';

/**
 * Status workflow RPS kursus ini; lihat juga tab Workflow. Status dan riwayat event datang dari
 * WorkflowLayout, yang memperbaruinya real-time (FE-10.2).
 */
export default function WorkflowOverviewPage() {
  const { course: workflow, events, connection, refresh } = useCourse();
  const release = useAction(() => setMoodleTarget(workflow.id, null));

  return (
    <div className="grid grid--2">
      <Card title="Status workflow">
        <ErrorAlert error={release.error} onClose={release.clearError} />
        <WorkflowConnectionNote workflow={workflow} connection={connection} />
        <WorkflowStatusPanel workflow={workflow} events={events} />
        <button type="button" className="btn mt-4" disabled={release.pending} onClick={() => release.run().then(refresh).catch(() => {})}>
          Lepas RPS dari kursus ini
        </button>
      </Card>
      <Card title="Aktivitas agent">
        <EventLog events={events} />
      </Card>
    </div>
  );
}
