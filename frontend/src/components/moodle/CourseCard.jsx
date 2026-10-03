import { Link } from 'react-router-dom';
import { withToken } from '../../services/moodle/moodleClient';
import { Badge } from '../ui';

/** Kartu course seperti block "My courses" / "Recently accessed courses" di Moodle. */
export default function CourseCard({ course, isTeacher }) {
  return (
    <Link
      to={`/course/${course.id}`}
      className="group flex flex-col overflow-hidden rounded-lg border border-line bg-white text-ink no-underline shadow-sm transition hover:shadow-md hover:text-ink"
    >
      <div
        className="h-28 bg-cover bg-center"
        style={{ backgroundImage: course.courseimage ? `url("${withToken(course.courseimage)}")` : undefined, backgroundColor: '#e3e7eb' }}
      />
      <div className="flex flex-1 flex-col gap-1 p-3.5">
        {course.coursecategory && <span className="text-xs text-muted">{course.coursecategory}</span>}
        <span className="font-semibold text-primary group-hover:underline">{course.fullname}</span>
        <div className="mt-auto flex flex-wrap items-center gap-2 pt-2">
          <span className="text-xs text-muted">{course.shortname}</span>
          {isTeacher && <Badge tone="info">Dosen</Badge>}
        </div>
        {!isTeacher && course.hasprogress && course.progress != null && (
          <div className="pt-1.5">
            <div className="h-1.5 overflow-hidden rounded-full bg-line">
              <div className="h-full bg-primary" style={{ width: `${course.progress}%` }} />
            </div>
            <span className="text-xs text-muted">{Math.round(course.progress)}% selesai</span>
          </div>
        )}
      </div>
    </Link>
  );
}
