import { useCourse } from '../../../hooks/useCourse';
import { useAction, useApi } from '../../../hooks/useApi';
import { getWorkflowEvents, setMoodleTarget } from '../../../services/workflowService';
import { Badge, Card, ErrorAlert, ProgressBar } from '../../../components/ui';
import EventLog from '../../../components/ai/EventLog';

const STATUS = {
  QUEUED: ['Menunggu', 'neutral'],
  RUNNING: ['Berjalan', 'info'],
  COMPLETED: ['Selesai', 'success'],
  FAILED: ['Gagal', 'danger'],
};

/** Monitoring workflow RPS kursus ini (GET /workflows/{id} dan riwayat event-nya). */
export default function WorkflowOverviewPage() {
  const { course: workflow, version, refresh } = useCourse();
  const events = useApi(() => getWorkflowEvents(workflow.id), [workflow.id, version]);
  const release = useAction(() => setMoodleTarget(workflow.id, null));
  const [label, tone] = STATUS[workflow.status] ?? [workflow.status, 'neutral'];

  return (
    <div className="grid grid--2">
      <Card title="Status workflow">
        <ErrorAlert error={release.error} onClose={release.clearError} />
        <p className="mb-3"><Badge tone={tone}>{label}</Badge></p>
        {workflow.progress?.total > 0 && (
          <ProgressBar completed={workflow.progress.completed} total={workflow.progress.total} label={workflow.stage ?? ''} />
        )}
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
