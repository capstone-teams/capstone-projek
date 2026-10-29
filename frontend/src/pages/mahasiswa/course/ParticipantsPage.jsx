import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import ParticipantsTable from '../../../components/moodle/course/ParticipantsTable';

/** Peserta kursus untuk mahasiswa (tanpa email peserta lain). */
export default function ParticipantsPage() {
  const { course } = useMoodleCourse();
  return <ParticipantsTable courseId={course.id} />;
}
