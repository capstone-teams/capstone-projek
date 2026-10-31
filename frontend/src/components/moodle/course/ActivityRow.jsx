import { Link } from 'react-router-dom';
import { Badge } from '../../ui';
import ActivityIcon from '../ActivityIcon';
import MoodleHtml from '../MoodleHtml';
import { ActivityEditMenu, InlineNameEditor } from '../editing';
import { formatUnixDateTime } from '../../../utils/format';

const MOD_LABELS = {
  assign: 'Tugas',
  quiz: 'Kuis',
  forum: 'Forum',
  page: 'Halaman',
  url: 'URL',
  resource: 'File',
  folder: 'Folder',
  book: 'Buku',
  lesson: 'Lesson',
  h5pactivity: 'H5P',
};

const DATE_LABELS = { 'Opened:': 'Dibuka:', 'Due:': 'Tenggat:', 'Closes:': 'Ditutup:', 'Closed:': 'Ditutup:', 'Opens:': 'Dibuka:' };

// Indentasi aktivitas (Geser ke kanan) mengikuti Moodle: satu tingkat ≈ 1.5rem.
const indentStyle = (mod) => (mod.indent > 0 ? { marginLeft: `${Math.min(mod.indent, 16) * 1.5}rem` } : undefined);

/** Satu aktivitas di halaman kursus. Pada Edit mode menampilkan pensil ubah nama dan menu ⋮. */
export default function ActivityRow({ courseId, mod, isTeacher, editMode, sections, editing }) {
  const hidden = !mod.visible || mod.visibleoncoursepage === 0;
  const hiddenBadge = isTeacher && hidden && <Badge tone="warning">Disembunyikan dari mahasiswa</Badge>;
  const menu = editMode && <ActivityEditMenu activity={mod} sections={sections} editing={editing} />;

  if (mod.modname === 'label') {
    return (
      <li className={`flex items-start gap-2 px-1 py-2 ${editMode ? 'rounded-2xl border border-dashed border-line bg-white px-4' : ''}`} style={indentStyle(mod)}>
        <MoodleHtml html={mod.description} className="min-w-0 flex-1" />
        {hiddenBadge}
        {menu}
      </li>
    );
  }

  const title = mod.uservisible === false ? (
    <span className="font-semibold text-muted">{mod.name}</span>
  ) : (
    <Link to={`/course/${courseId}/mod/${mod.id}`} className="font-semibold">
      {mod.name}
    </Link>
  );

  return (
    // .activity-item (Moodle 5.3): padding 1.25rem, radius 1rem, latar abu muda, putih saat hover.
    <li
      className={`flex items-start gap-3 rounded-2xl border border-line-subtle bg-surface p-5 transition-colors hover:bg-white focus-within:outline-2 focus-within:outline-primary ${hidden && isTeacher ? 'opacity-80' : ''}`}
      style={indentStyle(mod)}
    >
      <ActivityIcon modname={mod.modname} src={mod.modicon} />
      <div className="min-w-0 flex-1">
        <div className="text-xs uppercase tracking-wide text-muted">{MOD_LABELS[mod.modname] ?? mod.modplural ?? mod.modname}</div>
        {editMode ? (
          <InlineNameEditor name={mod.name} itemLabel={mod.name} disabled={!!editing.pending} onSave={(name) => editing.renameCm(mod, name)}>
            {title}
          </InlineNameEditor>
        ) : title}
        {mod.dates?.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-x-4 text-sm">
            {mod.dates.map((d) => (
              <span key={d.label}>
                <strong>{DATE_LABELS[d.label] ?? d.label}</strong> {formatUnixDateTime(d.timestamp)}
              </span>
            ))}
          </div>
        )}
        {mod.availabilityinfo && <div className="mt-1 text-sm text-muted">Dibatasi: {mod.availabilityinfo.replace(/<[^>]+>/g, ' ')}</div>}
      </div>
      {hiddenBadge}
      {mod.completiondata?.state === 1 && <Badge tone="success">Selesai</Badge>}
      {menu}
    </li>
  );
}
