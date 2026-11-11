import { Link, useSearchParams } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { useApi } from '../../../hooks/useApi';
import { useOnChange } from '../../../hooks/useOnChange';
import { useWorkflowMonitor } from '../../../hooks/useWorkflowMonitor';
import { PLAN_STATUS, getWorkflowPlan } from '../../../services/coursePlanService';
import { listWorkflowContents } from '../../../services/contentService';
import {
  hasContentGenerationActivity,
  isWorkflowFinished,
} from '../../../utils/workflowStatus';
import { Card, EmptyState } from '../../../components/ui';
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

  const existingItems = contents.data ?? [];
  const showMatrix = Boolean(contents.error) || hasContentGenerationActivity(workflow, events, existingItems);

  return (
    <div className="stack">
      <WorkflowContentTriggerCard
        workflowId={workflowId}
        workflow={workflow}
        events={events}
        plan={plan.data}
        planLoading={plan.loading}
        planError={plan.error}
        onRetryPlan={() => plan.reload()}
        hasExistingContents={existingItems.length > 0}
        onStarted={() => {
          onWorkflowUpdated?.();
          contents.reload({ silent: true });
        }}
      />

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
    </div>
  );
}
