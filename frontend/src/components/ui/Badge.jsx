import { STATUS_LABELS, statusTone } from '../../utils/workflow';

const BADGE_TONES = {
  neutral: 'bg-surface text-ink border border-line',
  success: 'bg-success-light text-success',
  warning: 'bg-warning-light text-warning',
  danger: 'bg-danger-light text-danger',
  info: 'bg-primary-light text-primary',
  primary: 'bg-primary text-white',
};

export function Badge({ tone = 'neutral', children }) {
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded px-2 py-0.5 text-xs font-bold ${BADGE_TONES[tone] ?? BADGE_TONES.neutral}`}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }) {
  return <Badge tone={statusTone(status)}>{STATUS_LABELS[status] ?? status}</Badge>;
}
