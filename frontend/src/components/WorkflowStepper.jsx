import { WORKFLOW_STEPS, currentStepIndex } from '../utils/workflow';

export default function WorkflowStepper({ status }) {
  const current = currentStepIndex(status);
  const finished = status === 'COMPLETED';

  return (
    <ol className="stepper" aria-label="Tahapan workflow">
      {WORKFLOW_STEPS.map((step, i) => {
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
