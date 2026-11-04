import { useApi } from '../../hooks/useApi';
import { usePolling } from '../../hooks/usePolling';
import { useWorkflowEvents } from '../../hooks/useWorkflowEvents';
import { getWorkflow, getWorkflowEvents } from '../../services/workflowService';
import { isWorkflowFinished } from '../../utils/workflowStatus';
import { formatDateTime } from '../../utils/format';
import { Card, ErrorAlert, Spinner } from '../ui';
import EventLog from './EventLog';
import WorkflowStatusPanel from './WorkflowStatusPanel';

// Polling hanya cadangan: event workflow (WebSocket §17) memicu pembaruan lebih cepat.
const POLL_MS = 4000;

/**
 * Detail satu workflow: GET /workflows/{id} dan riwayat event-nya. Diperbarui otomatis lewat event
 * workflow, dengan polling sebagai cadangan sampai workflow COMPLETED atau FAILED.
 * `onChanged` dipanggil setelah data diperbarui (mis. agar daftar ikut disegarkan).
 */
export default function WorkflowDetail({ workflowId, rpsName, onChanged }) {
  const { data, error, loading, reload } = useApi(
    () => Promise.all([getWorkflow(workflowId), getWorkflowEvents(workflowId)]).then(([workflow, events]) => ({ workflow, events })),
    [workflowId],
  );
  const refresh = async () => {
    await reload({ silent: true });
    onChanged?.();
  };
  const workflow = data?.workflow;
  usePolling(refresh, POLL_MS, !!workflow && !isWorkflowFinished(workflow));
  useWorkflowEvents([workflowId], refresh);

  if (loading && !data) return <Spinner label="Memuat status workflow…" />;
  if (error && !data) return <ErrorAlert error={error} />;

  return (
    <div className="flex flex-col gap-4">
      <ErrorAlert error={error} />
      <Card title={rpsName ?? 'Status workflow'}>
        <p className="mb-3 text-sm text-muted">Dibuat {formatDateTime(workflow.created_at)} · Diperbarui {formatDateTime(workflow.updated_at)}</p>
        <WorkflowStatusPanel workflow={workflow} events={data.events} />
      </Card>
      <Card title="Aktivitas agent">
        <EventLog events={data.events} />
      </Card>
    </div>
  );
}
