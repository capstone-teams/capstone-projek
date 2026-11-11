import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAction } from '../../../hooks/useApi';
import { PLAN_STATUS, PLAN_STATUS_META } from '../../../services/coursePlanService';
import { generateWorkflowContents } from '../../../services/contentService';
import { COURSE_PLAN_ACTIVITY_LABELS, isExamWeek, weekTypeLabel } from '../../../utils/coursePlan';
import {
  WORKFLOW_API_STATUS,
  WORKFLOW_STATUS,
  contentGenerationFailureOf,
  contentGenerationProgressOf,
  isWorkflowBusy,
} from '../../../utils/workflowStatus';
import { Alert, Badge, Card, ErrorAlert, ProgressBar, Spinner } from '../../ui';
import ActivityConfigPanel from './ActivityConfigPanel';

const MAX_VISIBLE_TOPICS = 3;

const PROGRESS_LABELS = {
  [WORKFLOW_STATUS.GENERATING_CONTENT]: 'Membuat konten mingguan…',
  [WORKFLOW_STATUS.VALIDATING]: 'Memvalidasi hasil konten…',
  [WORKFLOW_STATUS.RETRYING]: 'Memperbaiki dan mencoba ulang konten…',
};

function unapprovedMessage(status) {
  if (!status) return 'Workflow ini belum memiliki course plan. Susun dan setujui course plan terlebih dahulu di tab Rencana.';
  if (status === PLAN_STATUS.REJECTED) return 'Course plan ditolak dan perlu direvisi/disetujui terlebih dahulu di tab Rencana sebelum generate konten.';
  return 'Course plan belum disetujui. Periksa dan setujui rencana kuliah di tab Rencana sebelum melakukan generate konten.';
}

function submitLabel({ pending, selectedCount, allSelected }) {
  if (pending) return 'Memulai generation…';
  if (selectedCount === 0) return 'Generate Konten';
  if (allSelected) return 'Generate Semua Minggu';
  return `Generate ${selectedCount} Minggu Terpilih`;
}

function WeekPlanCard({ week, checked, disabled, onToggle }) {
  const exam = isExamWeek(week);
  const typeLabel = weekTypeLabel(week);
  const objectives = week.objectives ?? [];
  const topics = week.topics ?? [];
  const activities = week.planned_activities ?? [];

  const cardTone = exam
    ? 'cursor-not-allowed border-line bg-surface/80 text-muted opacity-65'
    : disabled
    ? 'cursor-not-allowed border-line bg-surface/60 text-muted opacity-80'
    : checked
    ? 'cursor-pointer border-primary/70 bg-white ring-1 ring-primary/15 shadow-sm hover:border-primary'
    : 'cursor-pointer border-line bg-white shadow-xs hover:border-primary/60';

  return (
    <li className="h-full">
      <label
        title={exam ? `${typeLabel}: tidak menghasilkan konten` : week.title}
        className={`flex h-full flex-col justify-between gap-3 rounded-lg border p-4 transition-all ${cardTone}`}
      >
        <div className="flex flex-col gap-2.5">
          <div className="flex items-start justify-between gap-2">
            <div className="flex flex-wrap items-baseline gap-2">
              <span
                aria-hidden="true"
                className={`text-2xl leading-none font-bold tabular-nums ${exam ? 'text-muted' : 'text-primary'}`}
              >
                {week.week_number}
              </span>
              <span className="text-xs font-medium text-muted">
                Minggu {week.week_number}
              </span>
              {typeLabel && (
                <Badge tone={exam ? 'neutral' : 'info'}>{typeLabel}</Badge>
              )}
            </div>
            <input
              type="checkbox"
              checked={checked}
              disabled={disabled}
              aria-label={`Minggu ${week.week_number}: ${week.title}`}
              className="mt-0.5 size-4 shrink-0 accent-primary"
              onChange={onToggle}
            />
          </div>

          <h4 className="m-0 line-clamp-2 text-[15px] leading-snug font-semibold text-ink">
            {week.title || `Minggu ${week.week_number}`}
          </h4>

          {exam ? (
            <p className="m-0 text-xs text-muted">
              Minggu ujian · tidak menghasilkan konten pembelajaran.
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {objectives.length > 0 && (
                <p
                  className="m-0 line-clamp-2 text-xs leading-relaxed text-ink-subtle"
                  title={objectives.join(' ')}
                >
                  <span className="font-semibold text-muted">Tujuan: </span>
                  {objectives.join(' · ')}
                </p>
              )}

              {topics.length > 0 && (
                <div className="text-xs text-muted">
                  <span className="font-semibold">Topik:</span>
                  <ul className="m-0 mt-1 list-disc space-y-0.5 pl-4 text-ink-subtle">
                    {topics.slice(0, MAX_VISIBLE_TOPICS).map((topic, index) => (
                      <li key={index} className="truncate" title={topic}>
                        {topic}
                      </li>
                    ))}
                  </ul>
                  {topics.length > MAX_VISIBLE_TOPICS && (
                    <span className="mt-0.5 inline-block text-[11px] text-muted">
                      +{topics.length - MAX_VISIBLE_TOPICS} topik lainnya
                    </span>
                  )}
                </div>
              )}

              {objectives.length === 0 && topics.length === 0 && (
                <p className="m-0 text-xs text-muted">
                  Belum ada rincian tujuan atau topik pada rencana minggu ini.
                </p>
              )}
            </div>
          )}
        </div>

        {!exam && (
          <div className="mt-auto flex flex-wrap items-center gap-1.5 border-t border-line/70 pt-2.5">
            {activities.length > 0 ? (
              activities.map((activity, index) => (
                <Badge key={`${activity}-${index}`} tone="neutral">
                  {COURSE_PLAN_ACTIVITY_LABELS[activity] ?? activity}
                </Badge>
              ))
            ) : (
              <span className="text-[11px] text-muted">Belum ada rencana aktivitas</span>
            )}
          </div>
        )}
      </label>
    </li>
  );
}

/**
 * Trigger dan pemilihan minggu langsung berbasis card checklist untuk generate konten workflow (FE-16.1).
 * Setiap card menampilkan nomor pertemuan bergaya tampilan kursus, judul minggu, ringkasan tujuan
 * pembelajaran, daftar singkat topik, dan rencana aktivitas dari response /plan.
 */
export default function WorkflowContentTriggerCard({
  workflowId,
  workflow,
  events = [],
  plan,
  planLoading = false,
  planError = null,
  onRetryPlan,
  hasExistingContents = false,
  onStarted,
}) {
  const [excluded, setExcluded] = useState([]);
  const [startedNotice, setStartedNotice] = useState(null);

  const generate = useAction((weeks) => generateWorkflowContents(workflowId, weeks));

  const weeks = plan?.weeks ?? [];
  const generatableWeeks = weeks.filter((week) => !isExamWeek(week)).map((week) => week.week_number);
  const examCount = weeks.length - generatableWeeks.length;
  const selectedWeeks = generatableWeeks.filter((num) => !excluded.includes(num));
  const allSelected = generatableWeeks.length > 0 && selectedWeeks.length === generatableWeeks.length;

  const isPlanApproved = plan?.status === PLAN_STATUS.APPROVED;
  const planMeta = plan?.status
    ? (PLAN_STATUS_META[plan.status] ?? { label: plan.status, tone: 'neutral' })
    : { label: 'Belum ada', tone: 'neutral' };

  const generationStage = contentGenerationProgressOf(workflow, events);
  const busy = isWorkflowBusy(workflow);
  const completed = workflow?.status === WORKFLOW_API_STATUS.COMPLETED;
  const failureEvent = contentGenerationFailureOf(workflow, events);
  const controlsLocked = busy || completed || Boolean(generationStage) || generate.pending;

  const buttonDisabled = !workflowId
    || !isPlanApproved
    || controlsLocked
    || selectedWeeks.length === 0;

  const toggleWeek = (weekNumber) => {
    setExcluded((prev) => (
      prev.includes(weekNumber)
        ? prev.filter((item) => item !== weekNumber)
        : [...prev, weekNumber]
    ));
  };

  const handleToggleAll = () => {
    setExcluded(allSelected ? generatableWeeks : []);
  };

  const handleSubmit = () => {
    if (buttonDisabled) return;
    setStartedNotice(null);
    const payload = allSelected ? 'all' : selectedWeeks;
    generate
      .run(payload)
      .then((res) => {
        setStartedNotice(res?.message || 'Generation konten dijadwalkan.');
        return onStarted?.(res);
      })
      .catch(() => {});
  };

  if (planLoading && !plan) {
    return (
      <Card title="Generate Konten Mingguan">
        <Spinner label="Memuat ringkasan course plan…" />
      </Card>
    );
  }

  if (planError && !plan) {
    return (
      <Card title="Generate Konten Mingguan">
        <ErrorAlert error={planError} />
        {onRetryPlan && (
          <button type="button" className="btn btn--ghost btn--sm" onClick={onRetryPlan}>
            Coba lagi
          </button>
        )}
      </Card>
    );
  }

  return (
    <Card
      title={hasExistingContents ? 'Generate Ulang Konten Mingguan' : 'Generate Konten Mingguan'}
      actions={plan && (
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="neutral">Versi {plan.version ?? 1}</Badge>
          <Badge tone={planMeta.tone}>{planMeta.label}</Badge>
        </div>
      )}
    >
      <div className="stack">
        <ErrorAlert error={generate.error} onClose={generate.clearError} />

        {startedNotice && !generationStage && (
          <Alert tone="info" onClose={() => setStartedNotice(null)}>
            {startedNotice}
          </Alert>
        )}

        {failureEvent && (
          <Alert tone="danger" title="Generation konten gagal">
            {failureEvent.message || 'Proses pembuatan konten berhenti karena kesalahan.'}
          </Alert>
        )}

        {generationStage && (
          <div className="rounded-lg border border-line bg-surface p-3.5" role="status">
            {workflow?.progress?.total > 0 ? (
              <ProgressBar
                completed={workflow.progress.completed}
                total={workflow.progress.total}
                label={PROGRESS_LABELS[generationStage] ?? 'Memproses konten…'}
              />
            ) : (
              <Spinner label={PROGRESS_LABELS[generationStage] ?? 'Memproses konten…'} />
            )}
          </div>
        )}

        {!generationStage && busy && (
          <Alert tone="info" title="Workflow sedang berjalan">
            Proses lain sedang berlangsung pada workflow ini. Tunggu hingga selesai sebelum memulai generation konten.
          </Alert>
        )}

        {completed && (
          <Alert tone="success" title="Workflow selesai">
            Seluruh tahapan workflow ini telah selesai.
          </Alert>
        )}

        {!isPlanApproved && (
          <Alert tone="warning" title="Course plan belum disetujui">
            <p>{unapprovedMessage(plan?.status)}</p>
            <Link to="../plan" relative="path" className="btn btn--secondary btn--sm mt-2">
              Buka Tab Rencana →
            </Link>
          </Alert>
        )}

        {isPlanApproved && (
          <section className="flex flex-col gap-3" aria-label="Pilih minggu generation">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
              <div className="min-w-0">
                <h3 className="m-0 text-sm font-semibold text-ink">
                  Course Plan{plan.course?.title ? ` — ${plan.course.title}` : ''}
                </h3>
                <p className="m-0 mt-0.5 text-xs text-muted">
                  {selectedWeeks.length} dari {generatableWeeks.length} minggu dipilih · Total {weeks.length} minggu
                  {examCount > 0 ? ` (${examCount} minggu ujian dilewati)` : ''}
                </p>
              </div>

              {generatableWeeks.length > 0 && (
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={controlsLocked}
                  onClick={handleToggleAll}
                >
                  {allSelected ? 'Kosongkan pilihan' : 'Pilih semua minggu'}
                </button>
              )}
            </div>

            {weeks.length > 0 && (
              <>
                <ActivityConfigPanel mode="readonly" plan={plan} />
                <ul
                  className="m-0 grid list-none gap-3 p-0 md:grid-cols-2 lg:grid-cols-3"
                  aria-label="Daftar minggu course plan"
                >
                {weeks.map((week) => {
                  const exam = isExamWeek(week);
                  const checked = !exam && !excluded.includes(week.week_number);
                  const disabled = exam || controlsLocked;
                  return (
                    <WeekPlanCard
                      key={week.week_number}
                      week={week}
                      checked={checked}
                      disabled={disabled}
                      onToggle={() => toggleWeek(week.week_number)}
                    />
                  );
                })}
                </ul>
              </>
            )}
          </section>
        )}

        <div className="form__actions">
          <button
            type="button"
            className="btn btn--primary"
            disabled={buttonDisabled}
            onClick={handleSubmit}
          >
            {submitLabel({
              pending: generate.pending,
              selectedCount: isPlanApproved ? selectedWeeks.length : 0,
              allSelected: isPlanApproved && allSelected,
            })}
          </button>
        </div>
      </div>
    </Card>
  );
}
