import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import MoodleHtml from '../MoodleHtml';

/**
 * Kerangka halaman kursus yang sama untuk dosen dan mahasiswa: ringkasan kursus, tombol
 * Buka/Tutup semua, lompat ke #section-N, dan daftar section. Isi tiap section dirender halaman
 * pemanggil lewat `renderSection(section, { collapsed, onToggle })`.
 */
export default function CourseOutline({ course, sections, renderSection, before, after }) {
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

      {before}
      {sections.map((s) => renderSection(s, { collapsed: !!collapsed[s.id], onToggle: () => setCollapsed((c) => ({ ...c, [s.id]: !c[s.id] })) }))}
      {after}
    </div>
  );
}
