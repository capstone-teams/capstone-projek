import { Badge } from '../ui';
import { workflowStatusMeta } from '../../utils/workflowStatus';

/**
 * Badge status workflow. Penanda dibedakan bentuknya, tidak hanya warnanya:
 * putaran = berjalan, ↻ = mencoba ulang, ! = menunggu tindakan dosen, ✓ = selesai, ✕ = gagal.
 */
export default function WorkflowStatusBadge({ workflow }) {
  const meta = workflowStatusMeta(workflow);
  return (
    <Badge tone={meta.tone}>
      <span className="inline-flex items-center gap-1.5" title={meta.description} data-marker={meta.marker}>
        {meta.marker === 'running' && (
          <span aria-hidden="true" className="inline-block size-2.5 animate-spin rounded-full border-2 border-current border-t-transparent motion-reduce:animate-none" />
        )}
        {meta.marker === 'retry' && <span aria-hidden="true">↻</span>}
        {meta.marker === 'review' && <span aria-hidden="true">!</span>}
        {meta.marker === 'done' && <span aria-hidden="true">✓</span>}
        {meta.marker === 'failed' && <span aria-hidden="true">✕</span>}
        <span>{meta.label}</span>
      </span>
    </Badge>
  );
}
