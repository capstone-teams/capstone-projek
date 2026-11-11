import { useMemo, useState } from 'react';
import {
  EVENT_TYPE,
  EVENT_TYPE_META,
  STAGE_LABELS,
  WORKFLOW_EVENT,
  WORKFLOW_EVENT_LABELS,
  countEventTypes,
  eventTimeline,
} from '../../utils/workflowStatus';
import { formatTimestamp } from '../../utils/format';
import { Badge, EmptyState } from '../ui';

const ALL = 'all';

// Kegagalan dan percobaan ulang dibedakan warna dan bentuk penanda (✕ / ↻), sama seperti indikator tahap FE-10.1.
const ITEM_STYLE = {
  [EVENT_TYPE.ERROR_FAILURE]: { box: 'border-danger bg-danger-light', dot: 'bg-danger text-white', glyph: '✕' },
  [EVENT_TYPE.RETRY_FIX]: { box: 'border-warning bg-warning-light', dot: 'border-2 border-warning bg-warning-light text-warning', glyph: '↻' },
};
const DEFAULT_STYLE = { box: 'border-line bg-white', dot: 'border border-line bg-surface text-muted', glyph: '•' };

function FilterButton({ active, label, count, onClick }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`btn btn--sm ${active ? 'btn--primary' : 'btn--ghost'}`}
    >
      {label} <span className="opacity-80">({count})</span>
    </button>
  );
}

/**
 * Riwayat event workflow sebagai timeline (FE-10.3): seluruh event dari GET /workflows/{id}/events, dari yang
 * terbaru di atas sampai yang paling lama, dengan jenis event, tahap, pesan, dan waktu. Dapat disaring per jenis
 * event; bila workflow dijalankan ulang, tiap proses diberi judul di atas event-nya (proses terbaru lebih dulu).
 */
export default function WorkflowEventTimeline({ events = [] }) {
  const [filter, setFilter] = useState(ALL);
  const timeline = useMemo(() => eventTimeline(events), [events]);
  const counts = useMemo(() => countEventTypes(timeline), [timeline]);
  const runs = timeline.at(-1)?.run ?? 0;
  const types = Object.values(EVENT_TYPE).filter((type) => counts[type]);
  // Filter yang jenisnya tidak lagi ada (mis. riwayat berganti) kembali ke semua event.
  const active = filter !== ALL && !counts[filter] ? ALL : filter;
  // Terbaru di atas: aktivitas agent yang sedang berjalan langsung terlihat tanpa menggulir.
  const shown = (active === ALL ? timeline : timeline.filter((event) => event.type === active)).slice().reverse();

  if (!timeline.length) return <EmptyState title="Belum ada event." />;

  return (
    <div>
      <div role="group" aria-label="Filter jenis event" className="mb-4 flex flex-wrap gap-2">
        <FilterButton active={active === ALL} label="Semua" count={timeline.length} onClick={() => setFilter(ALL)} />
        {types.map((type) => (
          <FilterButton key={type} active={active === type} label={EVENT_TYPE_META[type].label} count={counts[type]} onClick={() => setFilter(type)} />
        ))}
      </div>
      <ol className="m-0 flex max-h-[70vh] list-none flex-col overflow-y-auto p-0 pr-1" aria-label="Riwayat event workflow">
        {shown.map((event, index) => {
          const style = ITEM_STYLE[event.type] ?? DEFAULT_STYLE;
          const meta = EVENT_TYPE_META[event.type];
          // Judul proses tampil di atas event pertama (terbaru) tiap proses.
          const runStart = active === ALL && runs > 1 && (index === 0 || shown[index - 1].run !== event.run);
          return (
            <li key={`${event.timestamp}-${event.event}-${index}`} data-event-type={event.type} data-event={event.event} className="flex gap-3">
              <span className="flex flex-col items-center" aria-hidden="true">
                <span className={`mt-3 grid size-6 shrink-0 place-items-center rounded-full text-xs font-bold ${style.dot}`}>{style.glyph}</span>
                {index < shown.length - 1 && <span className="w-px flex-1 bg-line" />}
              </span>
              <div className="min-w-0 flex-1 pb-3">
                {runStart && <p className="mb-1 mt-2 text-xs font-semibold uppercase tracking-wide text-muted">Proses ke-{event.run}</p>}
                <div className={`rounded-lg border px-3 py-2 ${style.box}`}>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                    <Badge tone={meta.tone}>{meta.label}</Badge>
                    <span className="font-semibold">{WORKFLOW_EVENT_LABELS[event.event] ?? event.event}</span>
                    {event.stage && <span className="text-muted">· {STAGE_LABELS[event.stage] ?? event.stage}</span>}
                    <time dateTime={event.timestamp} className="ml-auto text-xs text-muted">{formatTimestamp(event.timestamp)}</time>
                  </div>
                  {event.message && <p className="mt-1 text-sm wrap-anywhere">{event.message}</p>}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
