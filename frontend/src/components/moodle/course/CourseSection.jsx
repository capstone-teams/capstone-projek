import { useState } from 'react';
import { Badge } from '../../ui';
import MoodleHtml from '../MoodleHtml';
import { AddActivityModal, InlineNameEditor, SectionEditMenu } from '../editing';
import ActivityRow from './ActivityRow';
import { COURSE_CARD } from './courseCard';

/**
 * Satu section kursus, mengikuti LMS ITK.
 * - Dengan `onClose`: panel pertemuan yang dibuka dari tile (judul bergaris bawah biru, tombol ×), berisi
 *   ringkasan (Sub-CPMK, bahan kajian) lalu kartu aktivitas.
 * - Tanpa `onClose` (section umum): judul sebagai kartu bergaris biru di kiri, lalu tiap aktivitas sebagai
 *   kartu sendiri.
 * Pada Edit mode: ubah nama, menu ⋮, dan tombol tambah aktivitas.
 */
export default function CourseSection({ course, section, sections, isTeacher, onClose, editMode, editing }) {
  const [adding, setAdding] = useState(false);
  const modules = section.modules.filter((m) => isTeacher || m.uservisible !== false || m.availabilityinfo);
  const hidden = section.visible === 0;
  const panel = !!onClose;

  const heading = (
    <h3 className={`text-2xl font-bold text-ink max-phone:text-xl ${panel ? 'inline-block border-b-[3px] border-primary pb-1' : ''}`}>
      {section.name}
    </h3>
  );
  const header = (
    <div className="flex items-start gap-2">
      <div className={`flex min-w-0 flex-1 flex-wrap items-center gap-2 ${panel ? '' : 'border-l-4 border-primary pl-3'}`}>
        {editMode ? (
          <InlineNameEditor name={section.name} itemLabel={section.name} disabled={!!editing.pending} onSave={(name) => editing.renameSection(section, name)}>
            {heading}
          </InlineNameEditor>
        ) : heading}
        {isTeacher && hidden && <Badge tone="warning">Disembunyikan dari mahasiswa</Badge>}
      </div>
      {editMode && <SectionEditMenu section={section} editing={editing} />}
      {panel && (
        <button
          type="button"
          className="grid size-9 shrink-0 cursor-pointer place-items-center rounded-full text-2xl leading-none text-muted hover:bg-surface hover:text-ink"
          aria-label={`Tutup ${section.name}`}
          onClick={onClose}
        >
          <span aria-hidden="true">×</span>
        </button>
      )}
    </div>
  );
  const activities = (
    <>
      {modules.length > 0 && (
        <ul className="flex flex-col gap-3">
          {modules.map((m) => (
            <ActivityRow key={m.id} courseId={course.id} mod={m} isTeacher={isTeacher} editMode={editMode} sections={sections} editing={editing} />
          ))}
        </ul>
      )}
      {panel && !modules.length && <p className="text-sm text-muted">Belum ada aktivitas.</p>}
      {editMode && (
        <button
          type="button"
          className="flex w-full cursor-pointer items-center gap-3 rounded-md border border-dashed border-primary/50 bg-white px-4 py-3 text-left font-semibold text-primary transition-colors hover:bg-primary-light"
          onClick={() => setAdding(true)}
        >
          <span aria-hidden="true" className="grid size-7 place-items-center rounded-md border border-primary text-lg leading-none">+</span>
          Tambah aktivitas atau sumber
        </button>
      )}
      {adding && <AddActivityModal open courseId={course.id} section={section} onClose={() => setAdding(false)} />}
    </>
  );

  if (panel) {
    return (
      <section id={`section-${section.section}`} className={`${COURSE_CARD} scroll-mt-20 flex flex-col gap-4 border-primary/40 p-5`} aria-label={section.name}>
        {header}
        {section.summary && <MoodleHtml html={section.summary} className="text-ink" />}
        {activities}
      </section>
    );
  }

  return (
    <section id={`section-${section.section}`} className="scroll-mt-20 flex flex-col gap-3" aria-label={section.name}>
      {(section.name || section.summary || editMode) && (
        <div className={COURSE_CARD}>
          {header}
          {section.summary && <MoodleHtml html={section.summary} className="mt-2 text-sm text-ink" />}
        </div>
      )}
      {activities}
    </section>
  );
}
