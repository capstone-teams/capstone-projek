import { Badge } from '../ui';
import { rpsStatusMeta } from '../../utils/rpsStatus';

const MARKERS = {
  running: <span aria-hidden="true" className="inline-block size-2.5 animate-spin rounded-full border-2 border-current border-t-transparent motion-reduce:animate-none" />,
  done: <span aria-hidden="true">✓</span>,
  failed: <span aria-hidden="true">✕</span>,
  idle: <span aria-hidden="true" className="inline-block size-1.5 rounded-full bg-current" />,
};

/** Badge status RPS dengan penanda visual (berputar = sedang berjalan). Dipakai juga FE-11.1. */
export default function RpsStatusBadge({ status }) {
  const meta = rpsStatusMeta(status);
  return (
    <Badge tone={meta.tone}>
      <span className="inline-flex items-center gap-1.5" title={meta.description}>
        {MARKERS[meta.marker]}
        <span>{meta.label}</span>
      </span>
    </Badge>
  );
}
