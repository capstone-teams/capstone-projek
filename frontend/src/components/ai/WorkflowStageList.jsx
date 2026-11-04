import { STAGE_STATE, STAGE_STATE_LABELS, deriveStages } from '../../utils/workflowStatus';

const DOT = {
  [STAGE_STATE.DONE]: 'bg-success text-white',
  [STAGE_STATE.RUNNING]: 'bg-primary text-white',
  [STAGE_STATE.REVIEW]: 'bg-warning text-white',
  [STAGE_STATE.RETRYING]: 'border-2 border-warning bg-warning-light text-warning',
  [STAGE_STATE.FAILED]: 'bg-danger text-white',
  [STAGE_STATE.PENDING]: 'border border-line bg-surface text-muted',
};
const TEXT = {
  [STAGE_STATE.DONE]: 'text-success',
  [STAGE_STATE.RUNNING]: 'text-primary',
  [STAGE_STATE.REVIEW]: 'font-semibold text-warning',
  [STAGE_STATE.RETRYING]: 'font-semibold text-warning',
  [STAGE_STATE.FAILED]: 'font-semibold text-danger',
  [STAGE_STATE.PENDING]: 'text-muted',
};

function Dot({ state, index }) {
  if (state === STAGE_STATE.RUNNING) {
    return <span aria-hidden="true" className="inline-block size-3 animate-spin rounded-full border-2 border-white border-t-transparent motion-reduce:animate-none" />;
  }
  const glyph = { [STAGE_STATE.DONE]: '✓', [STAGE_STATE.REVIEW]: '!', [STAGE_STATE.RETRYING]: '↻', [STAGE_STATE.FAILED]: '✕' }[state];
  return <span aria-hidden="true">{glyph ?? index + 1}</span>;
}

/**
 * Indikator urutan tahap workflow: selesai, berjalan, menunggu tindakan dosen, mencoba ulang, gagal, atau menunggu.
 * Keadaan dihitung dari data backend oleh deriveStages().
 */
export default function WorkflowStageList({ workflow, events }) {
  const stages = deriveStages(workflow, events);
  const finished = ['COMPLETED', 'FAILED'].includes(workflow?.status);

  return (
    <ol className="m-0 flex list-none flex-col gap-2 p-0" aria-label="Tahapan workflow">
      {stages.map((stage, index) => {
        const label = finished && stage.state === STAGE_STATE.PENDING ? 'Belum dijalankan' : STAGE_STATE_LABELS[stage.state];
        return (
          <li
            key={stage.stage}
            data-stage={stage.stage}
            data-state={stage.state}
            aria-current={[STAGE_STATE.RUNNING, STAGE_STATE.REVIEW, STAGE_STATE.RETRYING].includes(stage.state) ? 'step' : undefined}
            className="flex items-center gap-3 text-sm"
          >
            <span className={`grid size-6 shrink-0 place-items-center rounded-full text-xs font-bold ${DOT[stage.state]}`}>
              <Dot state={stage.state} index={index} />
            </span>
            <span className="min-w-0 flex-1">{stage.label}</span>
            <span className={`shrink-0 text-xs ${TEXT[stage.state]}`}>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
