import { Alert, ProgressBar } from '../ui';
import WorkflowStageList from './WorkflowStageList';
import WorkflowStatusBadge from './WorkflowStatusBadge';
import {
  STAGE_LABELS,
  WORKFLOW_EVENT,
  WORKFLOW_STAGE,
  needsInstructorAction,
  workflowStatusMeta,
} from '../../utils/workflowStatus';

/**
 * Status satu workflow: badge, kemajuan, catatan yang butuh perhatian, dan indikator tahap.
 * Data dari GET /workflows/{id} dan GET /workflows/{id}/events (design-api §16).
 */
export default function WorkflowStatusPanel({ workflow, events = [] }) {
  const meta = workflowStatusMeta(workflow);
  const failure = workflow.status === 'FAILED' ? [...events].reverse().find((event) => event.event === WORKFLOW_EVENT.FAILED) : null;
  const retry = workflow.stage === WORKFLOW_STAGE.RETRYING ? [...events].reverse().find((event) => event.event === WORKFLOW_EVENT.RETRY) : null;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <WorkflowStatusBadge workflow={workflow} />
        <span className="text-sm text-muted">{meta.description}</span>
      </div>

      {workflow.progress?.total > 0 && (
        <ProgressBar completed={workflow.progress.completed} total={workflow.progress.total} label={STAGE_LABELS[workflow.stage] ?? 'Kemajuan'} />
      )}

      {needsInstructorAction(workflow) && (
        <Alert tone="warning" title="Menunggu tindakan Anda">Workflow berhenti sampai Anda memeriksa hasilnya dan menyetujui atau menolaknya.</Alert>
      )}
      {retry && (
        <Alert tone="warning" title="Mencoba ulang">{retry.message ?? 'Tahap gagal sebagian dan sedang diperbaiki otomatis.'}</Alert>
      )}
      {workflow.status === 'FAILED' && (
        <Alert tone="danger" title="Workflow gagal">{failure?.message ?? 'Workflow berhenti karena kesalahan.'}</Alert>
      )}

      <WorkflowStageList workflow={workflow} events={events} />
    </div>
  );
}
