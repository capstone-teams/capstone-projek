import ActivityIcon from '../ActivityIcon';
import MoodleHtml from '../MoodleHtml';
import { COURSE_CARD } from './courseCard';

/** Satu kartu standar: ikon kotak berwarna, nama, keterangan belum tersedia, dan deskripsi dalam kotak abu-abu. */
export function GeneralCard({ card }) {
  return (
    <div className={COURSE_CARD} aria-label={card.name}>
      <div className="flex items-center gap-3">
        <ActivityIcon modname={card.modname} boxed />
        <div className="min-w-0 flex-1">
          <span className="font-semibold text-ink">{card.name}</span>
          <p className="text-xs text-muted">Belum tersedia</p>
        </div>
      </div>
      {card.description && <MoodleHtml html={card.description} className="mt-3 rounded bg-surface p-3 text-sm" />}
    </div>
  );
}
