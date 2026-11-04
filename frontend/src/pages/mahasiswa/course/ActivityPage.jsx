import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import AssignSubmission from '../../../components/moodle/AssignSubmission';
import ActivityView from '../../../components/moodle/course/ActivityView';

/** Aktivitas untuk mahasiswa: tugas menampilkan status dan tombol Add/Edit submission. */
export default function ActivityPage() {
  const { course } = useMoodleCourse();
  return (
    <ActivityView
      renderAssign={(assign, mod) => <AssignSubmission assign={assign} editPath={`/course/${course.id}/mod/${mod.id}/editsubmission`} />}
    />
  );
}
