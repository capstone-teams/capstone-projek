import { WORKFLOW_STEPPER_STEPS, deriveStepperState } from '../../utils/workflowStatus';

export default function WorkflowStepper({ workflow = null, events = [], plan = null, contents = null, executions = null }) {
  const { current, finished } = deriveStepperState(workflow, events, { plan, contents, executions });

  return (
    <ol className="stepper" aria-label="Tahapan workflow">
      {WORKFLOW_STEPPER_STEPS.map((step, i) => {
        const state = i < current || finished ? 'done' : i === current ? 'current' : 'todo';
        return (
          <li key={step.key} className={`stepper__item stepper__item--${state}`} aria-current={state === 'current' ? 'step' : undefined}>
            <span className="stepper__dot">{state === 'done' ? '✓' : i + 1}</span>
            <span className="stepper__label">{step.label}</span>
          </li>
        );
      })}
    </ol>
  );
}
