import { percent } from '../../utils/format';

export function ProgressBar({ completed = 0, total = 0, label }) {
  const value = percent(completed, total);
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between gap-2 text-sm text-muted">
        <span>{label}</span>
        <span>
          {completed}/{total} ({value}%)
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-line" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full bg-primary transition-[width] duration-300" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
