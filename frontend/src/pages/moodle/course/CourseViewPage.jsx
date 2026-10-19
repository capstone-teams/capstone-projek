import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { Badge } from '../../../components/ui';
import ActivityIcon from '../../../components/moodle/ActivityIcon';
import MoodleHtml from '../../../components/moodle/MoodleHtml';
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

function ActivityRow({ courseId, mod, isTeacher }) {
  if (mod.modname === 'label') {
    return (
      <li className="px-1 py-2">
        <MoodleHtml html={mod.description} />
      </li>
    );
  }
  const hidden = !mod.visible || mod.visibleoncoursepage === 0;
  return (
    // .activity-item (Moodle 5.3): padding 1.25rem, radius 1rem, latar abu muda, putih saat hover.
    <li className="flex items-start gap-3 rounded-2xl border border-line-subtle bg-surface p-5 transition-colors hover:bg-white focus-within:outline-2 focus-within:outline-primary">
      <ActivityIcon modname={mod.modname} src={mod.modicon} />
      <div className="min-w-0 flex-1">
        <div className="text-xs uppercase tracking-wide text-muted">{MOD_LABELS[mod.modname] ?? mod.modplural ?? mod.modname}</div>
        {mod.uservisible === false ? (
          <span className="font-semibold text-muted">{mod.name}</span>
        ) : (
          <Link to={`/course/${courseId}/mod/${mod.id}`} className="font-semibold">
            {mod.name}
          </Link>
        )}
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
      {isTeacher && hidden && <Badge tone="warning">Tersembunyi dari mahasiswa</Badge>}
      {mod.completiondata?.state === 1 && <Badge tone="success">Selesai</Badge>}
    </li>
  );
}

export default function CourseViewPage() {
  const { course, sections, isTeacher } = useMoodleCourse();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState({});

  // Lompat ke section dari link di indeks kursus (#section-N).
  useEffect(() => {
    if (!location.hash) return;
    document.getElementById(location.hash.slice(1))?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [location.hash]);

  const allCollapsed = sections.every((s) => collapsed[s.id]);
  const toggleAll = () => setCollapsed(allCollapsed ? {} : Object.fromEntries(sections.map((s) => [s.id, true])));

  return (
    <div className="flex flex-col gap-4">
      {course.summary && (
        <div className="rounded-2xl border border-line-subtle bg-white p-4">
          <MoodleHtml html={course.summary} />
          {course.contacts?.length > 0 && (
            <p className="mt-2 text-sm">
              <strong>Pengajar:</strong> {course.contacts.map((c) => c.fullname).join(', ')}
            </p>
          )}
        </div>
      )}

      <div className="flex justify-end">
        <button type="button" className="btn btn--ghost btn--sm" onClick={toggleAll}>
          {allCollapsed ? 'Buka semua' : 'Tutup semua'}
        </button>
      </div>

      {sections.map((s) => {
        const isCollapsed = collapsed[s.id];
        const visibleMods = s.modules.filter((m) => isTeacher || m.uservisible !== false || m.availabilityinfo);
        if (!isTeacher && s.uservisible === false) return null;
        return (
          // .course-section .section-item: kartu putih, border gray-200, radius 1rem.
          <section key={s.id} id={`section-${s.section}`} className="scroll-mt-20 rounded-2xl border border-line-subtle bg-white">
            <div className="flex items-center gap-2 p-4">
              <button
                type="button"
                className="grid size-8 cursor-pointer place-items-center rounded-full bg-primary-light text-primary hover:bg-primary hover:text-white"
                aria-expanded={!isCollapsed}
                aria-label={isCollapsed ? 'Buka section' : 'Tutup section'}
                onClick={() => setCollapsed((c) => ({ ...c, [s.id]: !c[s.id] }))}
              >
                <span className={`text-sm transition-transform ${isCollapsed ? '-rotate-90' : ''}`}>▾</span>
              </button>
              <h3 className="text-xl font-bold text-ink">{s.name}</h3>
              {isTeacher && s.visible === 0 && <Badge tone="warning">Tersembunyi</Badge>}
            </div>
            {!isCollapsed && (
              <div>
                {s.summary && <MoodleHtml html={s.summary} className="pr-4 pb-4 pl-16 text-ink" />}
                {/* .section-content-inner: border-top, latar gray-100, sudut bawah membulat. */}
                <div className="rounded-b-2xl border-t border-line-subtle bg-surface p-4">
                {visibleMods.length ? (
                  <ul className="flex flex-col gap-2">
                    {visibleMods.map((m) => (
                      <ActivityRow key={m.id} courseId={course.id} mod={m} isTeacher={isTeacher} />
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted">Belum ada aktivitas.</p>
                )}
                </div>
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
