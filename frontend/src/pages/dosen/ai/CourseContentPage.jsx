import { Link, useSearchParams } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { useApi } from '../../../hooks/useApi';
import { useOnChange } from '../../../hooks/useOnChange';
import { useWorkflowMonitor } from '../../../hooks/useWorkflowMonitor';
import { getContent } from '../../../services/courseService';
import { PLAN_STATUS, getWorkflowPlan } from '../../../services/coursePlanService';
import { listWorkflowContents } from '../../../services/contentService';
import {
  hasContentGenerationActivity,
  isWorkflowFinished,
} from '../../../utils/workflowStatus';
import { Badge, Card, EmptyState, ErrorAlert, ProgressBar, Spinner } from '../../../components/ui';
import ContentGeneratePanel from '../../../components/ai/course/ContentGeneratePanel';
import ContentGenerationMatrix from '../../../components/ai/course/ContentGenerationMatrix';
import WeekContentDetail from '../../../components/ai/course/WeekContentDetail';
import WorkflowContentTriggerCard from '../../../components/ai/course/WorkflowContentTriggerCard';

const CAN_GENERATE = ['PLAN_APPROVED', 'WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED'];
const CAN_REGENERATE = ['WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED'];
const BEFORE_PLAN_APPROVED = ['CREATED', 'PLANNING', 'WAITING_PLAN_REVIEW'];

/**
 * Halaman Generate Weekly Content (FE-16):
 * - Bila `workflowId` tersedia (backend nyata / alur berbasis workflow), memakai API
 *   `/workflows/{id}/plan` dan `/workflows/{id}/contents/...` (FE-16.1).
 * - Bila hanya ada project kursus legacy tanpa workflow (mode mock E2E), memakai `<ProjectContent />`.
 */
export default function CourseContentPage() {
  const { course, workflow: projectWorkflow, workflowId: projectWorkflowId, events: projectEvents = [], refresh } = useCourse();
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

  if (course?.id) {
    return <ProjectContent />;
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

function ProjectContent() {
  const { course, version, refresh } = useCourse();
  const [params, setParams] = useSearchParams();
  const content = useApi(() => getContent(course.id), [course.id, version]);
  const weeks = content.data?.weeks ?? [];

  if (BEFORE_PLAN_APPROVED.includes(course.status)) {
    return (
      <Card>
        <EmptyState title="Rencana belum disetujui.">Konten mingguan dapat digenerate setelah rencana course disetujui.</EmptyState>
      </Card>
    );
  }

  const selectedWeek = Number(params.get('week')) || weeks[0]?.week;
  const selected = weeks.find((w) => w.week === selectedWeek);
  const generating = course.status === 'GENERATING_CONTENT' || course.status === 'VALIDATING';

  return (
    <div className="stack">
      {generating && (
        <Card>
          {course.status === 'VALIDATING' ? (
            <Spinner label="Memvalidasi konten terhadap RPS…" />
          ) : (
            course.progress && (
              <ProgressBar completed={course.progress.completed} total={course.progress.total} label={`Generate konten · ${course.stage ?? ''}`} />
            )
          )}
        </Card>
      )}

      {CAN_GENERATE.includes(course.status) && <ContentGeneratePanel course={course} hasContent={weeks.length > 0} onStarted={refresh} />}

      <ErrorAlert error={content.error} />
      {content.loading && !content.data ? (
        <Spinner />
      ) : weeks.length === 0 ? (
        !generating && (
          <Card>
            <EmptyState title="Belum ada konten." />
          </Card>
        )
      ) : (
        <div className="grid grid--sidebar">
          <Card title="Minggu">
            <ul className="week-nav">
              {weeks.map((w) => (
                <li key={w.week}>
                  <button
                    type="button"
                    className={`week-nav__btn ${w.week === selectedWeek ? 'week-nav__btn--active' : ''}`}
                    onClick={() => setParams({ week: String(w.week) }, { replace: true })}
                  >
                    <span className="week-nav__num">{w.week}</span>
                    <span className="week-nav__topic">{w.topic}</span>
                    {w.revision > 0 && <Badge tone="info">r{w.revision}</Badge>}
                  </button>
                </li>
              ))}
            </ul>
          </Card>
          {selected && (
            <WeekContentDetail week={selected} course={course} canRegenerate={CAN_REGENERATE.includes(course.status)} onStarted={refresh} />
          )}
        </div>
      )}
    </div>
  );
}
