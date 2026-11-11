import { Link } from 'react-router-dom';
import { Badge } from '../../ui';
import ActivityIcon from '../ActivityIcon';
import MoodleHtml from '../MoodleHtml';
import { ActivityEditMenu, InlineNameEditor } from '../editing';
import { formatUnixDateTime } from '../../../utils/format';
import { htmlToText, readingMinutes } from '../../../utils/htmlText';
import { DIRECT_MOODLE_EDITING } from '../../../services/moodle/courseEditing';
import { COURSE_CARD } from './courseCard';

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

// Rujukan Moodle: indentasi aktivitas (Geser ke kanan), satu tingkat ≈ 1.5rem.
const indentStyle = (mod) => (mod.indent > 0 ? { marginLeft: `${Math.min(mod.indent, 16) * 1.5}rem` } : undefined);
// Gateway menyertakan intro lengkap di `mod.description` untuk assign/quiz agar tampil di halaman aktivitas;
// di kartu ringkasan kursus teks panjangnya disembunyikan kecuali ditandai `showdescription === 1`.
const INLINE_HIDDEN_MODNAMES = new Set(['assign', 'quiz', 'page']);

/**
 * Status penyelesaian di pojok kanan kartu seperti LMS ITK: "✓ Selesai" bila sudah selesai, selain itu tombol
 * "Tandai selesai" untuk mahasiswa (nonaktif karena endpoint penyelesaian belum tersedia).
 */
function Completion({ mod, isTeacher }) {
  if (mod.completiondata?.state === 1) {
    return (
      <span className="shrink-0 rounded bg-success px-2 py-0.5 text-xs font-bold whitespace-nowrap text-white">
        <span aria-hidden="true">✓ </span>Selesai
      </span>
    );
  }
  if (isTeacher) return null;
  return (
    <button
      type="button"
      className="shrink-0 rounded border border-ink-subtle bg-white px-2 py-0.5 text-xs whitespace-nowrap text-ink-subtle disabled:cursor-not-allowed"
      disabled
      title="Fitur ini belum tersedia."
    >
      Tandai selesai
    </button>
  );
}

/** Satu aktivitas di halaman kursus sebagai kartu tersendiri. Pada Edit mode menampilkan pensil ubah nama dan menu ⋮. */
export default function ActivityRow({ courseId, mod, isTeacher, editMode, sections, editing }) {
  const hidden = !mod.visible || mod.visibleoncoursepage === 0;
  const hiddenBadge = isTeacher && hidden && <Badge tone="warning">Disembunyikan dari mahasiswa</Badge>;
  const menu = editMode && <ActivityEditMenu activity={mod} sections={sections} editing={editing} />;

  if (mod.modname === 'label') {
    return (
      <li className={`${COURSE_CARD} flex items-start gap-2 ${editMode ? 'border-dashed' : ''}`} style={indentStyle(mod)}>
        <MoodleHtml html={mod.description} className="min-w-0 flex-1 text-sm" />
        {hiddenBadge}
        <Completion mod={mod} isTeacher={isTeacher} />
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
    <li className={`${COURSE_CARD} focus-within:outline-2 focus-within:outline-primary ${hidden && isTeacher ? 'opacity-80' : ''}`} style={indentStyle(mod)}>
      <div className="flex items-center gap-3">
        <ActivityIcon modname={mod.modname} src={mod.modicon} boxed />
        <div className="min-w-0 flex-1">
          <span className="sr-only">{MOD_LABELS[mod.modname] ?? mod.modplural ?? mod.modname}: </span>
          {editMode ? (
            <InlineNameEditor name={mod.name} itemLabel={mod.name} disabled={!!editing.pending || !DIRECT_MOODLE_EDITING} onSave={(name) => editing.renameCm(mod, name)}>
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
        <Completion mod={mod} isTeacher={isTeacher} />
        {menu}
      </div>
      {/* Deskripsi yang ditampilkan di halaman kursus (mis. petunjuk folder); isi assign/quiz/page tampil saat dibuka. */}
      {Boolean(mod.description) && (!INLINE_HIDDEN_MODNAMES.has(mod.modname) || mod.showdescription === 1) && (
        <MoodleHtml html={mod.description} className="mt-3 rounded bg-surface p-3 text-sm" />
      )}
      {mod.modname === 'page' && mod.uservisible !== false && mod.content && !editMode && (
        <PagePreview courseId={courseId} mod={mod} />
      )}
    </li>
  );
}

// Materi lebih panjang dari ini dipotong di kartu dan dibaca utuh di halaman artikel.
const PREVIEW_MAX_CHARS = 600;

/**
 * Pratinjau isi Page (materi mingguan) langsung di kartu pertemuan. Materi panjang dipotong dengan efek pudar dan
 * tombol "Baca selengkapnya" yang membuka halaman artikel (`/course/:id/mod/:cmid`).
 */
function PagePreview({ courseId, mod }) {
  const text = htmlToText(mod.content);
  if (!text) return null;
  const long = text.length > PREVIEW_MAX_CHARS;
  return (
    <div className="mt-3 border-t border-line-subtle pt-3">
      <div className={long ? 'relative max-h-56 overflow-hidden' : undefined} data-testid="page-preview">
        <MoodleHtml html={mod.content} className="text-sm text-ink" />
        {long && <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-linear-to-t from-white to-transparent" />}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
        <Link to={`/course/${courseId}/mod/${mod.id}`} className="font-semibold">
          {long ? 'Baca selengkapnya →' : 'Buka halaman materi →'}
        </Link>
        <span className="text-muted">± {readingMinutes(text)} menit baca</span>
      </div>
    </div>
  );
}
