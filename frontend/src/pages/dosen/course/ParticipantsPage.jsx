import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import ParticipantsTable from '../../../components/moodle/course/ParticipantsTable';

/** Peserta kursus untuk dosen, termasuk email mahasiswa. */
export default function ParticipantsPage() {
  const { course } = useMoodleCourse();
  return <ParticipantsTable courseId={course.id} showEmail />;
}
