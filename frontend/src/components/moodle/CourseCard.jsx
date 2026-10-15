import { Link } from 'react-router-dom';
<<<<<<< HEAD
import { Badge, StatusBadge } from '../ui';
=======
<<<<<<< HEAD
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
=======
import { Badge } from '../ui';
import styles from '../../features/dashboard/DashboardPage.module.css';
>>>>>>> 8a5a3ec2c6308f208b58dd368f4aa3cdb9316534

const META_CLASS = 'text-[13px] text-muted';

/** aiStatus: status project generator AI (dosen saja); null = belum dimulai, undefined = tidak ditampilkan. */
export default function CourseCard({ course, isTeacher, aiStatus }) {
  return <Link to={'/course/' + course.id} className="flex min-h-[200px] cursor-pointer flex-col justify-between gap-4 rounded-lg border border-line bg-white p-6 transition-all duration-150 ease-[ease] hover:border-[#93C5FD] hover:shadow-[0_4px_6px_-1px_rgba(0,0,0,0.05)]">
    <div className="flex flex-col gap-1"><span className="text-[12px] font-semibold tracking-[0.05em] text-muted uppercase">{course.shortname}</span><span className="text-[18px] font-bold text-ink">{course.fullname}</span>{course.coursecategory && <span className={META_CLASS}>{course.coursecategory}</span>}</div>
    <div className="flex items-center justify-between border-t border-line-subtle pt-3"><div className="flex flex-wrap items-center gap-1.5">{isTeacher ? <Badge tone="info">Dosen</Badge> : <Badge tone="success">Mahasiswa</Badge>}{aiStatus !== undefined && (aiStatus ? <span title="Status generator AI"><StatusBadge status={aiStatus} /></span> : <Badge>AI belum dimulai</Badge>)}</div><span className={META_CLASS}>Buka kursus →</span></div>
    {!isTeacher && course.hasprogress && course.progress != null && <div>
      <div className="h-1.5 overflow-hidden rounded-full bg-line"><div className="h-full bg-primary" style={{ width: course.progress + '%' }} /></div>
      <span className={META_CLASS}>{Math.round(course.progress)}% selesai</span>
    </div>}
  </Link>;
>>>>>>> origin/develop
}
