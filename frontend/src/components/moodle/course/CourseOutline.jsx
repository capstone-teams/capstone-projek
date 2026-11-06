import { Fragment, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import MoodleHtml from '../MoodleHtml';
import { COURSE_CARD } from './courseCard';
import { GeneralCard } from './GeneralCards';
import { ANNOUNCEMENT_CARD, GENERAL_CARDS } from './generalCardData';

/**
 * Kerangka halaman kursus untuk dosen dan mahasiswa, mengikuti LMS ITK: di atas deretan kartu (pengumuman,
 * `before`, deskripsi mata kuliah, presensi, surat sakit/izin, section umum), di bawahnya satu tile bernomor per
 * pertemuan (format Tiles). Tile yang diklik membuka panel selebar grid tepat di bawah baris tile tersebut; tile
 * lain diredupkan. Link #section-N
 * membuka tile N. Isi section dirender halaman pemanggil lewat `renderSection(section, { onClose })`; section
 * umum (section 0) dirender tanpa `onClose`.
 */
export default function CourseOutline({ course, sections, renderSection, before, after }) {
  const location = useLocation();
  // Pilihan tile berlaku selama hash URL belum berubah; hash baru (#section-N) memilih tile sendiri.
  const [choice, setChoice] = useState({ hash: null, id: null });

  const general = sections.filter((s) => s.section === 0);
  const tiles = sections.filter((s) => s.section !== 0);
  // Kartu standar hanya tampil bila section umum belum berisi aktivitas jenis yang sama.
  const generalMods = new Set(general.flatMap((s) => s.modules.map((m) => m.modname)));
  const standard = (card) => !generalMods.has(card.modname);
  const hashSection = tiles.find((s) => `#section-${s.section}` === location.hash);
  const openId = choice.hash === location.hash ? choice.id : hashSection?.id ?? null;
  const select = (id) => setChoice({ hash: location.hash, id });

  // Lompat ke section dari link di indeks kursus atau breadcrumb (#section-N).
  useEffect(() => {
    if (!location.hash) return;
    document.getElementById(location.hash.slice(1))?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [location.hash]);

  return (
    <div className="flex flex-col gap-3">
      {standard(ANNOUNCEMENT_CARD) && <GeneralCard card={ANNOUNCEMENT_CARD} />}
      {before}
      {course.summary && (
        <div className={COURSE_CARD}>
          <p className="font-bold text-ink">Deskripsi Mata Kuliah:</p>
          <MoodleHtml html={course.summary} />
          {course.contacts?.length > 0 && (
            <p className="mt-2 text-sm">
              <strong>Pengajar:</strong> {course.contacts.map((c) => c.fullname).join(', ')}
            </p>
          )}
        </div>
      )}
      {GENERAL_CARDS.filter(standard).map((card) => <GeneralCard key={card.key} card={card} />)}
      {general.map((s) => renderSection(s, {}))}

      {tiles.length > 0 && (
        // grid-flow-row-dense: panel selebar grid turun ke baris berikutnya, sisa tile mengisi baris tile terpilih.
        <ul className="mt-3 grid grid-flow-row-dense grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6" aria-label="Pertemuan">
          {tiles.map((s) => {
            const open = s.id === openId;
            const dimmed = openId != null && !open;
            return (
              <Fragment key={s.id}>
                <li>
                  <button
                    type="button"
                    className={`flex h-full w-full cursor-pointer flex-col items-start gap-2 rounded-md border bg-white p-4 text-left shadow-sm transition hover:border-primary focus-visible:outline-2 focus-visible:outline-primary ${
                      open ? 'border-primary' : 'border-line'
                    } ${dimmed ? 'opacity-50 hover:opacity-100' : ''}`}
                    aria-expanded={open}
                    aria-controls={open ? `section-${s.section}` : undefined}
                    onClick={() => select(open ? null : s.id)}
                  >
                    <span aria-hidden="true" className="text-3xl leading-none font-bold text-primary">{s.section}</span>
                    <span className="line-clamp-3 text-sm font-semibold text-ink">{s.name}</span>
                    {s.visible === 0 && <span className="text-xs text-warning">Disembunyikan</span>}
                  </button>
                </li>
                {open && <li className="col-span-full">{renderSection(s, { onClose: () => select(null) })}</li>}
              </Fragment>
            );
          })}
        </ul>
      )}
      {after}
    </div>
  );
}
