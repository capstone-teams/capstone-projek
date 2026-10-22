import { Badge, EmptyState } from '../ui';
import { RPS_STATUS } from '../../services/rpsService';
import { RPS_STATUS_LABELS, RPS_STATUS_TONES } from '../../utils/workflow';
import { formatDateTime } from '../../utils/format';

const CAN_PROCESS = [RPS_STATUS.UPLOADED, RPS_STATUS.FAILED];

/** Daftar RPS milik dosen (kartu ringkas): status pemrosesan, workflow, dan aksi proses ulang. */
export default function RpsList({ items, highlightId, processingId, onProcess }) {
  if (!items.length) {
    return <EmptyState title="Belum ada RPS.">Unggah RPS pertama Anda untuk memulai analisis.</EmptyState>;
  }
  return (
    <ul className="m-0 flex list-none flex-col gap-3 p-0" aria-label="Daftar RPS" aria-live="polite">
      {items.map((item) => (
        <li key={item.id} className={`rounded-lg border border-line p-3 ${item.id === highlightId ? 'bg-primary-light' : ''}`}>
          <div className="flex items-start justify-between gap-2 font-semibold">
            <div className="min-w-0">
              <span className="wrap-anywhere">{item.filename}</span>
              {item.id === highlightId && <span className="ml-2 text-xs font-normal text-primary">Baru</span>}
            </div>
            <Badge tone={RPS_STATUS_TONES[item.status] ?? 'neutral'}>{RPS_STATUS_LABELS[item.status] ?? item.status}</Badge>
          </div>
          {item.status === RPS_STATUS.FAILED && item.processing_error_message && (
            <p className="mt-1 text-sm text-danger">{item.processing_error_message}</p>
          )}
          <dl className="mt-2 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
            <dt className="text-muted">Diunggah</dt>
            <dd>{formatDateTime(item.created_at)}</dd>
            <dt className="text-muted">Workflow</dt>
            <dd>{item.workflow_id ? <code className="wrap-anywhere">{item.workflow_id}</code> : <span className="muted">Belum dibuat</span>}</dd>
          </dl>
          {CAN_PROCESS.includes(item.status) && (
            <button
              type="button"
              className="btn btn--ghost btn--sm mt-2"
              disabled={processingId === item.id}
              onClick={() => onProcess(item)}
            >
              {processingId === item.id ? 'Memulai…' : item.status === RPS_STATUS.FAILED ? 'Proses ulang' : 'Proses'}
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}
