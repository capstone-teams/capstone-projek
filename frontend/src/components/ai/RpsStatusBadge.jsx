import { Badge } from '../ui';
import { rpsStatusMeta } from '../../utils/rpsStatus';

/** Badge status RPS; warna menandai hasil, indikator berputar menandai proses yang masih berjalan. */
export default function RpsStatusBadge({ status }) {
  const meta = rpsStatusMeta(status);
  return (
    <Badge tone={meta.tone}>
      <span className="inline-flex items-center gap-1.5" title={meta.description}>
        {meta.marker === 'running' && (
          <span aria-hidden="true" className="inline-block size-2.5 animate-spin rounded-full border-2 border-current border-t-transparent motion-reduce:animate-none" />
        )}
        <span>{meta.label}</span>
      </span>
    </Badge>
  );
}
