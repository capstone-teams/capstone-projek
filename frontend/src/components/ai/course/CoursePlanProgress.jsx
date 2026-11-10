import { WORKFLOW_STAGE, WORKFLOW_STATUS, retryingStageOf } from '../../../utils/workflowStatus';

const STEPS = [
  { stage: WORKFLOW_STAGE.COURSE_PLANNING, label: 'Menyusun rencana' },
  { stage: WORKFLOW_STAGE.VALIDATION, label: 'Memvalidasi rencana' },
  { stage: null, label: 'Siap direview' },
];

const TITLES = {
  [WORKFLOW_STATUS.PLANNING_COURSE]: 'Agent sedang menyusun rencana…',
  [WORKFLOW_STATUS.VALIDATING]: 'Agent sedang memvalidasi rencana…',
  [WORKFLOW_STATUS.RETRYING]: 'Agent sedang mencoba ulang…',
};

const MARKERS = {
  done: 'bg-success text-white',
  running: 'bg-primary text-white',
  retrying: 'bg-warning text-white',
  pending: 'bg-line text-muted',
};
const STATE_LABELS = { done: 'Selesai', running: 'Berjalan', retrying: 'Mencoba ulang', pending: 'Menunggu' };

/**
 * Indikator progres course planning (FE-12.1) dari status workflow yang diperbarui event real-time (FE-10.2):
 * PLANNING_COURSE → VALIDATING → siap direview, dengan RETRYING pada tahap yang sedang dicoba ulang.
 */
export default function CoursePlanProgress({ progress, events, replacing = false }) {
  const activeStage = progress === WORKFLOW_STATUS.RETRYING
    ? retryingStageOf(events)
    : progress === WORKFLOW_STATUS.VALIDATING ? WORKFLOW_STAGE.VALIDATION : WORKFLOW_STAGE.COURSE_PLANNING;
  const activeIndex = Math.max(STEPS.findIndex((step) => step.stage === activeStage), 0);
  const stateOf = (index) => {
    if (index < activeIndex) return 'done';
    if (index > activeIndex) return 'pending';
    return progress === WORKFLOW_STATUS.RETRYING ? 'retrying' : 'running';
  };

  return (
    <section className="mb-4 rounded-lg border border-primary/30 bg-primary-light/40 p-4" role="status" aria-live="polite" aria-label="Progres penyusunan rencana">
      <div className="flex items-center gap-2">
        <span className="size-4 shrink-0 animate-spin rounded-full border-2 border-line border-t-primary motion-reduce:animate-none" aria-hidden="true" />
        <p className="font-semibold text-ink">{TITLES[progress]}</p>
      </div>
      <p className="mt-1 text-sm text-muted">
        {replacing
          ? 'Rencana di bawah akan diganti otomatis setelah versi baru siap.'
          : 'Rencana tampil otomatis setelah selesai disusun; halaman tidak perlu dimuat ulang.'}
      </p>
      <ol className="mt-3 flex flex-wrap gap-x-6 gap-y-2">
        {STEPS.map((step, index) => {
          const state = stateOf(index);
          return (
            <li key={step.label} className="flex items-center gap-2 text-sm" aria-current={state === 'running' || state === 'retrying' ? 'step' : undefined}>
              <span aria-hidden="true" className={`grid size-6 place-items-center rounded-full text-xs font-bold ${MARKERS[state]}`}>
                {state === 'done' ? '✓' : index + 1}
              </span>
              <span className={state === 'pending' ? 'text-muted' : 'font-medium text-ink'}>{step.label}</span>
              <span className="sr-only">: {STATE_LABELS[state]}</span>
              {state === 'retrying' && <span className="text-xs font-semibold text-warning">Mencoba ulang</span>}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
