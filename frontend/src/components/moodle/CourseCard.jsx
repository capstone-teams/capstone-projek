import { Link } from 'react-router-dom';
import { Badge } from '../ui';

const META_CLASS = 'text-[13px] text-muted';

export default function CourseCard({ course, isTeacher }) {
  return <Link to={'/course/' + course.id} className="flex min-h-[200px] cursor-pointer flex-col justify-between gap-4 rounded-lg border border-line bg-white p-6 transition-all duration-150 ease-[ease] hover:border-[#93C5FD] hover:shadow-[0_4px_6px_-1px_rgba(0,0,0,0.05)]">
    <div className="flex flex-col gap-1"><span className="text-[12px] font-semibold tracking-[0.05em] text-muted uppercase">{course.shortname}</span><span className="text-[18px] font-bold text-ink">{course.fullname}</span>{course.coursecategory && <span className={META_CLASS}>{course.coursecategory}</span>}</div>
    <div className="flex items-center justify-between border-t border-line-subtle pt-3">{isTeacher ? <Badge tone="info">Dosen</Badge> : <Badge tone="success">Mahasiswa</Badge>}<span className={META_CLASS}>Buka kursus →</span></div>
    {!isTeacher && course.hasprogress && course.progress != null && <div>
      <div className="h-1.5 overflow-hidden rounded-full bg-line"><div className="h-full bg-primary" style={{ width: course.progress + '%' }} /></div>
      <span className={META_CLASS}>{Math.round(course.progress)}% selesai</span>
    </div>}
  </Link>;
}
