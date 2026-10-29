import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import CourseOutline from '../../../components/moodle/course/CourseOutline';
import CourseSection from '../../../components/moodle/course/CourseSection';

/** Halaman kursus untuk mahasiswa: hanya section yang terlihat, tanpa kontrol edit. */
export default function CourseViewPage() {
  const { course, sections } = useMoodleCourse();
  const visible = sections.filter((s) => s.uservisible !== false);

  return (
    <CourseOutline
      course={course}
      sections={visible}
      renderSection={(s, { collapsed, onToggle }) => (
        <CourseSection key={s.id} course={course} section={s} sections={visible} isTeacher={false} collapsed={collapsed} onToggle={onToggle} editMode={false} />
      )}
    />
  );
}
