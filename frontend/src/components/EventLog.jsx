import { describeEvent } from '../utils/workflow';
import { formatTime } from '../utils/format';
import { EmptyState } from './ui';

export default function EventLog({ events, limit = 30 }) {
  if (!events?.length) return <EmptyState title="Belum ada event." />;
  const shown = events.slice(-limit).reverse();

  return (
    <ul className="event-log">
      {shown.map((ev, i) => (
        <li key={`${ev.timestamp}-${ev.event}-${i}`}>
          <time>{formatTime(ev.timestamp)}</time>
          <span>{describeEvent(ev)}</span>
        </li>
      ))}
    </ul>
  );
}
