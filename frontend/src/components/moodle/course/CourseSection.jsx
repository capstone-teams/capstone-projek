import { useState } from 'react';
import { Badge } from '../../ui';
import MoodleHtml from '../MoodleHtml';
import { AddActivityModal, InlineNameEditor, SectionEditMenu } from '../editing';
import ActivityRow from './ActivityRow';

/** Satu section kursus (dapat dilipat). Pada Edit mode: ubah nama, menu ⋮, dan tombol tambah aktivitas. */
export default function CourseSection({ course, section, sections, isTeacher, collapsed, onToggle, editMode, editing }) {
  const [adding, setAdding] = useState(false);
  const modules = section.modules.filter((m) => isTeacher || m.uservisible !== false || m.availabilityinfo);
  const hidden = section.visible === 0;

  return (
    // .course-section .section-item: kartu putih, border gray-200, radius 1rem.
    <section id={`section-${section.section}`} className="scroll-mt-20 rounded-2xl border border-line-subtle bg-white" aria-label={section.name}>
      <div className="flex items-center gap-2 p-4">
        <button
          type="button"
          className="grid size-8 shrink-0 cursor-pointer place-items-center rounded-full bg-primary-light text-primary hover:bg-primary hover:text-white"
          aria-expanded={!collapsed}
          aria-label={collapsed ? `Buka section ${section.name}` : `Tutup section ${section.name}`}
          onClick={onToggle}
        >
          <span className={`text-sm transition-transform ${collapsed ? '-rotate-90' : ''}`}>▾</span>
        </button>
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
          {editMode ? (
            <InlineNameEditor name={section.name} itemLabel={section.name} disabled={!!editing.pending} onSave={(name) => editing.renameSection(section, name)}>
              <h3 className="text-xl font-bold text-ink">{section.name}</h3>
            </InlineNameEditor>
          ) : (
            <h3 className="text-xl font-bold text-ink">{section.name}</h3>
          )}
          {isTeacher && hidden && <Badge tone="warning">Disembunyikan dari mahasiswa</Badge>}
        </div>
        {editMode && <SectionEditMenu section={section} editing={editing} />}
      </div>

      {!collapsed && (
        <div>
          {section.summary && <MoodleHtml html={section.summary} className="pr-4 pb-4 pl-16 text-ink" />}
          {/* .section-content-inner: border-top, latar gray-100, sudut bawah membulat. */}
          <div className="rounded-b-2xl border-t border-line-subtle bg-surface p-4">
            {modules.length ? (
              <ul className="flex flex-col gap-2">
                {modules.map((m) => (
                  <ActivityRow key={m.id} courseId={course.id} mod={m} isTeacher={isTeacher} editMode={editMode} sections={sections} editing={editing} />
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">Belum ada aktivitas.</p>
            )}
            {editMode && (
              <button
                type="button"
                className="mt-3 flex w-full cursor-pointer items-center gap-3 rounded-2xl border border-dashed border-primary/50 bg-white px-4 py-3 text-left font-semibold text-primary transition-colors hover:bg-primary-light"
                onClick={() => setAdding(true)}
              >
                <span aria-hidden="true" className="grid size-7 place-items-center rounded-md border border-primary text-lg leading-none">+</span>
                Tambah aktivitas atau sumber
              </button>
            )}
          </div>
        </div>
      )}
      {adding && <AddActivityModal open courseId={course.id} section={section} editing={editing} onClose={() => setAdding(false)} />}
    </section>
  );
}
