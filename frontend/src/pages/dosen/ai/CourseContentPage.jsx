import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { useApi } from '../../../hooks/useApi';
import { useOnChange } from '../../../hooks/useOnChange';
import { useWorkflowMonitor } from '../../../hooks/useWorkflowMonitor';
import { PLAN_STATUS, getWorkflowPlan } from '../../../services/coursePlanService';
import { listWorkflowContents } from '../../../services/contentService';
import {
  WORKFLOW_API_STATUS,
  WORKFLOW_STATUS,
  contentGenerationFailureOf,
  contentGenerationProgressOf,
  hasContentGenerationActivity,
  isWorkflowBusy,
  isWorkflowFinished,
} from '../../../utils/workflowStatus';
import { Alert, Card, EmptyState, ProgressBar, Spinner } from '../../../components/ui';
import ContentGenerationMatrix from '../../../components/ai/course/ContentGenerationMatrix';
import WorkflowContentTriggerCard from '../../../components/ai/course/WorkflowContentTriggerCard';

/**
 * Halaman Generate Weekly Content (FE-16): menggunakan API workflow `/workflows/{id}/plan`
 * dan `/workflows/{id}/contents/...` untuk memicu pembuatan konten dan memantau progres per minggu.
 */
export default function CourseContentPage() {
  const { workflow: projectWorkflow, workflowId: projectWorkflowId, events: projectEvents = [], refresh } = useCourse();
  const [params] = useSearchParams();
  const workflowParam = params.get('workflow');
  const ownWorkflowId = workflowParam && workflowParam !== projectWorkflowId ? workflowParam : null;
  const own = useWorkflowMonitor(ownWorkflowId);

  const workflowId = workflowParam || projectWorkflowId;
  const workflow = ownWorkflowId ? own.workflow : projectWorkflow;
  const events = ownWorkflowId ? own.events : projectEvents;

  if (workflowId) {
    return (
      <WorkflowContent
        key={workflowId}
        workflowId={workflowId}
        workflow={workflow}
        events={events}
        onWorkflowUpdated={() => {
          own.reload?.();
          return refresh?.();
        }}
      />
    );
  }

  return (
    <Card title="Konten mingguan">
      <EmptyState title="Belum ada workflow untuk kursus ini.">
        Unggah dan proses RPS terlebih dahulu di tab <Link to="../rps" relative="path">RPS</Link>.
      </EmptyState>
    </Card>
  );
}

function WorkflowContent({ workflowId, workflow, events = [], onWorkflowUpdated }) {
  const plan = useApi(() => getWorkflowPlan(workflowId), [workflowId]);
  const contents = useApi(() => listWorkflowContents(workflowId), [workflowId]);

  const signature = workflow
    ? `${workflow.status}|${workflow.stage ?? ''}|${workflow.updated_at ?? ''}|${events.length}`
    : null;
  useOnChange(signature, () => {
    contents.reload({ silent: true });
    if (!plan.data || plan.data.status !== PLAN_STATUS.APPROVED || isWorkflowFinished(workflow)) {
      plan.reload({ silent: true });
    }
  }, 300);

  const [regenerateOpen, setRegenerateOpen] = useState(false);
  const existingItems = contents.data ?? [];
  const hasContents = existingItems.length > 0;
  const showMatrix = Boolean(contents.error) || hasContentGenerationActivity(workflow, events, existingItems);

  const trigger = (
    <WorkflowContentTriggerCard
      workflowId={workflowId}
      workflow={workflow}
      events={events}
      plan={plan.data}
      planLoading={plan.loading}
      planError={plan.error}
      onRetryPlan={() => plan.reload()}
      hasExistingContents={hasContents}
      onStarted={() => {
        setRegenerateOpen(false);
        onWorkflowUpdated?.();
        contents.reload({ silent: true });
      }}
    />
  );

  return (
    <div className="stack">
      {/* Sebelum ada konten, pemilihan minggu adalah langkah utama. Setelah ada, hasil generation yang utama dan
          pemilihan minggu untuk generate ulang diciutkan agar tidak mendorong hasilnya ke bawah. */}
      {!hasContents && trigger}

      {showMatrix && (
        <ContentGenerationMatrix
          workflowId={workflowId}
          workflow={workflow}
          events={events}
          plan={plan.data}
          contents={existingItems}
          contentsLoading={contents.loading}
          contentsError={contents.error}
          onRetryContents={() => contents.reload()}
          onRegenerated={() => {
            onWorkflowUpdated?.();
            contents.reload({ silent: true });
          }}
        />
      )}

      {hasContents && (regenerateOpen ? (
        <div className="stack">
          <div>
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => setRegenerateOpen(false)}>
              Tutup pemilihan minggu
            </button>
          </div>
          {trigger}
        </div>
      ) : (
        <CollapsedGenerateCard workflow={workflow} events={events} onOpen={() => setRegenerateOpen(true)} />
      ))}
    </div>
  );
}

const PROGRESS_LABELS = {
  [WORKFLOW_STATUS.GENERATING_CONTENT]: 'Membuat konten mingguan…',
  [WORKFLOW_STATUS.VALIDATING]: 'Memvalidasi hasil konten…',
  [WORKFLOW_STATUS.RETRYING]: 'Memperbaiki dan mencoba ulang konten…',
};

/** Ringkasan generate ulang saat konten sudah ada: progres/galat run terbaru dan pintu ke pemilihan minggu. */
function CollapsedGenerateCard({ workflow, events, onOpen }) {
  const generationStage = contentGenerationProgressOf(workflow, events);
  const failure = contentGenerationFailureOf(workflow, events);
  const locked = isWorkflowBusy(workflow) || workflow?.status === WORKFLOW_API_STATUS.COMPLETED;
  return (
    <Card title="Generate ulang konten">
      <div className="stack">
        {failure && (
          <Alert tone="danger" title="Generation konten gagal">
            {failure.message || 'Proses pembuatan konten berhenti karena kesalahan.'}
          </Alert>
        )}
        {generationStage && (
          <div role="status">
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
        <p className="text-sm text-muted">
          Klik sel berstatus Selesai pada matriks untuk membaca isi konten. Perbaikan satu konten, satu minggu, atau
          seluruh kursus dengan catatan revisi dilakukan di halaman Review.
        </p>
        <div className="flex flex-wrap gap-2">
          <Link to="../review" relative="path" className="btn btn--primary btn--sm">Buka halaman Review</Link>
          <button type="button" className="btn btn--ghost btn--sm" disabled={locked} onClick={onOpen}>
            Generate ulang per minggu…
          </button>
        </div>
      </div>
    </Card>
  );
}
