import { useCourse } from '../../../hooks/useCourse';
import { Card, EmptyState } from '../../../components/ui';
import MoodleExecutionCard from '../../../components/ai/course/MoodleExecutionCard';
import MoodleVerificationCard from '../../../components/ai/course/MoodleVerificationCard';
import MoodleSectionsCard from '../../../components/ai/course/MoodleSectionsCard';

const BEFORE_APPROVAL = ['CREATED', 'PLANNING', 'WAITING_PLAN_REVIEW', 'PLAN_APPROVED', 'GENERATING_CONTENT', 'VALIDATING', 'WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED'];

export default function CoursePublishPage() {
  const { course } = useCourse();

  return (
    <div className="stack">
      {/* Struktur mingguan dapat disiapkan di kursus target begitu rencana disetujui, sebelum konten dikirim. */}
      <MoodleSectionsCard />
      {BEFORE_APPROVAL.includes(course.status) ? (
        <Card>
          <EmptyState title="Konten belum disetujui.">
            Eksekusi ke Moodle hanya dapat dilakukan setelah seluruh konten direview dan disetujui.
          </EmptyState>
        </Card>
      ) : (
        <div className="grid grid--2">
          <MoodleExecutionCard />
          <MoodleVerificationCard />
        </div>
      )}
    </div>
  );
}
