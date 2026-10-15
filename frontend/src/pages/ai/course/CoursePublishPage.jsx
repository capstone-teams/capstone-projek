import { useCourse } from '../../../hooks/useCourse';
import { Card, EmptyState } from '../../../components/ui';
import MoodleExecutionCard from '../../../components/ai/course/MoodleExecutionCard';
import MoodleVerificationCard from '../../../components/ai/course/MoodleVerificationCard';

const BEFORE_APPROVAL = ['CREATED', 'PLANNING', 'WAITING_PLAN_REVIEW', 'PLAN_APPROVED', 'GENERATING_CONTENT', 'VALIDATING', 'WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED'];

export default function CoursePublishPage() {
  const { course } = useCourse();

  if (BEFORE_APPROVAL.includes(course.status)) {
    return (
      <Card>
        <EmptyState title="Konten belum disetujui.">
          Eksekusi ke Moodle hanya dapat dilakukan setelah seluruh konten direview dan disetujui.
        </EmptyState>
      </Card>
    );
  }

  return (
    <div className="grid grid--2">
      <MoodleExecutionCard />
      <MoodleVerificationCard />
    </div>
  );
}
