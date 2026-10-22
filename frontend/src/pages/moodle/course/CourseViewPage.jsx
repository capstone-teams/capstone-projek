import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useCourseEditing } from '../../../hooks/useCourseEditing';
import { ErrorAlert } from '../../../components/ui';
import MoodleHtml from '../../../components/moodle/MoodleHtml';
import CourseSection from '../../../components/moodle/course/CourseSection';

export default function CourseViewPage() {
  const { course, sections, isTeacher, editMode } = useMoodleCourse();
  const editing = useCourseEditing();
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

      {editMode && <ErrorAlert error={editing.error} onClose={editing.clearError} />}

      {sections.map((s) =>
        !isTeacher && s.uservisible === false ? null : (
          <CourseSection
            key={s.id}
            course={course}
            section={s}
            sections={sections}
            isTeacher={isTeacher}
            collapsed={!!collapsed[s.id]}
            onToggle={() => setCollapsed((c) => ({ ...c, [s.id]: !c[s.id] }))}
            editMode={editMode}
            editing={editing}
          />
        ),
      )}

      {editMode && (
        <button
          type="button"
          className="btn btn--ghost self-start"
          disabled={editing.pending === 'section_add'}
          onClick={editing.addSection}
        >
          {editing.pending === 'section_add' ? 'Menambahkan…' : '+ Tambah section'}
        </button>
      )}
    </div>
  );
}
