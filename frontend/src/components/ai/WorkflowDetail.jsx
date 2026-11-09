import { useEffect, useRef } from 'react';
import { useWorkflowMonitor } from '../../hooks/useWorkflowMonitor';
import { formatDateTime } from '../../utils/format';
import { Card, ErrorAlert, Spinner } from '../ui';
import WorkflowConnectionNote from './WorkflowConnectionNote';
import WorkflowEventTimeline from './WorkflowEventTimeline';
import WorkflowStatusPanel from './WorkflowStatusPanel';

// Event beruntun (satu tahap bisa menerbitkan belasan event dalam sekejap) digabung menjadi satu panggilan.
const CHANGED_DEBOUNCE_MS = 300;

/**
 * Detail satu workflow: GET /workflows/{id} dan riwayat event-nya, diperbarui real-time lewat WebSocket
 * dengan polling sebagai cadangan (useWorkflowMonitor, FE-10.2).
 * `onChanged` dipanggil sekali setelah status workflow berubah (mis. agar daftar ikut disegarkan).
 */
export default function WorkflowDetail({ workflowId, rpsName, onChanged }) {
  const { workflow, events, connection, loading, error } = useWorkflowMonitor(workflowId);

  const signature = workflow ? `${workflow.status}|${workflow.stage}|${workflow.updated_at}` : null;
  const seen = useRef(signature);
  const changed = useRef(onChanged);
  useEffect(() => {
    changed.current = onChanged;
  });
  useEffect(() => {
    if (!signature) return undefined;
    const previous = seen.current;
    seen.current = signature;
    if (!previous || previous === signature) return undefined;
    const timer = setTimeout(() => changed.current?.(), CHANGED_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [signature]);

  if (loading) return <Spinner label="Memuat status workflow…" />;
  if (error && !workflow) return <ErrorAlert error={error} />;

  return (
    <div className="flex flex-col gap-4">
      <ErrorAlert error={error} />
      <Card title={rpsName ?? 'Status workflow'}>
        <p className="mb-3 text-sm text-muted">Dibuat {formatDateTime(workflow.created_at)} · Diperbarui {formatDateTime(workflow.updated_at)}</p>
        <WorkflowConnectionNote workflow={workflow} connection={connection} />
        <WorkflowStatusPanel workflow={workflow} events={events} />
      </Card>
      <Card title="Riwayat event">
        <WorkflowEventTimeline events={events} />
      </Card>
    </div>
  );
}
