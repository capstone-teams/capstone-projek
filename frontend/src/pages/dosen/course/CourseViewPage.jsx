import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useCourseEditing } from '../../../hooks/useCourseEditing';
import { ErrorAlert } from '../../../components/ui';
import CourseOutline from '../../../components/moodle/course/CourseOutline';
import CourseSection from '../../../components/moodle/course/CourseSection';

/**
 * Halaman kursus untuk dosen: semua section termasuk yang disembunyikan dari mahasiswa, dan
 * kontrol mode edit bagi pengajar yang boleh mengubah kursus.
 */
export default function CourseViewPage() {
  const { course, sections, editMode } = useMoodleCourse();
  const editing = useCourseEditing();

  return (
    <CourseOutline
      course={course}
      sections={sections}
      before={editMode && <ErrorAlert error={editing.error} onClose={editing.clearError} />}
      renderSection={(s, { collapsed, onToggle }) => (
        <CourseSection
          key={s.id}
          course={course}
          section={s}
          sections={sections}
          isTeacher
          collapsed={collapsed}
          onToggle={onToggle}
          editMode={editMode}
          editing={editing}
        />
      )}
      after={
        editMode && (
          <button
            type="button"
            className="btn btn--ghost self-start"
            disabled={editing.pending === 'section_add'}
            onClick={editing.addSection}
          >
            {editing.pending === 'section_add' ? 'Menambahkan…' : '+ Tambah section'}
          </button>
        )
      }
    />
  );
}
