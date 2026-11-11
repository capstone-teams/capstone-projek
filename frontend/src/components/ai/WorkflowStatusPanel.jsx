import { Link } from 'react-router-dom';
import { Alert, ProgressBar } from '../ui';
import WorkflowStageList from './WorkflowStageList';
import { CONTENT_KIND_LABELS } from '../../services/contentService';
import { parseContentMessage } from '../../utils/contentEvents';
import WorkflowStatusBadge from './WorkflowStatusBadge';
import {
  AWAITED_ACTION_META,
  STAGE_LABELS,
  WORKFLOW_EVENT,
  WORKFLOW_STAGE,
  awaitedActionOf,
  needsInstructorAction,
  workflowStatusMeta,
} from '../../utils/workflowStatus';

/** Judul percobaan ulang; untuk konten (RETRY_FIX) memuat minggu dan jenis konten dari pesan backend. */
function retryTitle(event) {
  const content = parseContentMessage(event.message);
  return content?.kind ? `Mencoba ulang: Minggu ${content.week} · ${CONTENT_KIND_LABELS[content.kind]}` : 'Mencoba ulang';
}

/** Tautan cepat ke tab Generator AI tujuan; Plan Review membawa workflow dan RPS-nya agar rencana yang tepat terbuka. */
function quickLink(base, page, workflow) {
  if (page !== 'plan') return `${base}/${page}`;
  const params = new URLSearchParams({ workflow: workflow.id });
  if (workflow.rps_id) params.set('rps', workflow.rps_id);
  return `${base}/plan?${params}`;
}

/**
 * Status satu workflow: badge, kemajuan, catatan yang butuh perhatian, dan indikator tahap.
 * Data dari GET /workflows/{id} dan GET /workflows/{id}/events (design-api §16).
 * Saat WAITING_FOR_REVIEW, tindakan yang ditunggu dibaca dari event terakhir; `linkBase` (path relatif ke tab
 * Generator AI, mis. "..") menampilkan tautan cepat ke halaman tindakan tersebut.
 */
export default function WorkflowStatusPanel({ workflow, events = [], linkBase }) {
  const meta = workflowStatusMeta(workflow);
  const action = AWAITED_ACTION_META[awaitedActionOf(workflow, events)];
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
        <Alert tone="warning" title={action ? `Menunggu tindakan Anda: ${action.title}` : 'Menunggu tindakan Anda'}>
          <p>{action?.description ?? 'Workflow berhenti sampai Anda memeriksa hasilnya dan menyetujui atau menolaknya.'}</p>
          {action && linkBase && (
            <div className="mt-2 flex flex-wrap gap-2">
              <Link to={quickLink(linkBase, action.page, workflow)} relative="path" className="btn btn--primary btn--sm">
                {action.linkLabel}
              </Link>
              {action.secondary && (
                <Link to={quickLink(linkBase, action.secondary.page, workflow)} relative="path" className="btn btn--ghost btn--sm">
                  {action.secondary.label}
                </Link>
              )}
            </div>
          )}
        </Alert>
      )}
      {retry && (
        <Alert tone="warning" title={retryTitle(retry)}>{retry.message ?? 'Tahap gagal sebagian dan sedang diperbaiki otomatis.'}</Alert>
      )}
      {workflow.status === 'FAILED' && (
        <Alert tone="danger" title="Workflow gagal">{failure?.message ?? 'Workflow berhenti karena kesalahan.'}</Alert>
      )}

      <WorkflowStageList workflow={workflow} events={events} />
    </div>
  );
}
