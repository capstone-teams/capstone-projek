import { Link, useInRouterContext, useLocation } from 'react-router-dom';
import { WORKFLOW_STEPPER_STEPS, deriveStepperState, isStepReachable, viewingKeyFromPath } from '../../utils/workflowStatus';

function StepperMarkup({ current, finished, viewingKey, interactive }) {
  return (
    <ol className="stepper" aria-label="Tahapan dan navigasi Generator AI">
      {WORKFLOW_STEPPER_STEPS.map((step, i) => {
        const state = i < current || finished ? 'done' : i === current ? 'current' : 'todo';
        const isViewing = Boolean(viewingKey && viewingKey === step.key);
        const reachable = isStepReachable(i, { current, finished });
        const clickable = interactive && reachable && (step.key !== 'done' || finished);

        const body = (
          <>
            <span className="stepper__dot">{state === 'done' ? '✓' : i + 1}</span>
            <span className="stepper__label">{step.label}</span>
          </>
        );

        return (
          <li
            key={step.key}
            className={`stepper__item stepper__item--${state}${isViewing ? ' stepper__item--viewing' : ''}`}
            aria-current={state === 'current' ? 'step' : undefined}
          >
            {clickable ? (
              <Link
                to={step.to}
                className="stepper__link"
                aria-current={isViewing ? 'page' : undefined}
              >
                {body}
              </Link>
            ) : (
              <span
                className={`stepper__link${interactive && !reachable ? ' cursor-not-allowed opacity-60' : ''}`}
                aria-disabled={interactive && !reachable ? 'true' : undefined}
                title={interactive && !reachable ? 'Selesaikan tahap sebelumnya terlebih dahulu.' : undefined}
              >
                {body}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function RouterWorkflowStepper({ current, finished, interactive }) {
  const { pathname } = useLocation();
  const viewingKey = viewingKeyFromPath(pathname);
  return <StepperMarkup current={current} finished={finished} viewingKey={viewingKey} interactive={interactive} />;
}

export default function WorkflowStepper({
  workflow = null,
  events = [],
  plan = null,
  contents = null,
  executions = null,
  verifications = null,
  interactive = true,
}) {
  const inRouter = useInRouterContext();
  const { current, finished } = deriveStepperState(workflow, events, { plan, contents, executions, verifications });

  if (inRouter) {
    return <RouterWorkflowStepper current={current} finished={finished} interactive={interactive} />;
  }
  return <StepperMarkup current={current} finished={finished} viewingKey={null} interactive={false} />;
}
