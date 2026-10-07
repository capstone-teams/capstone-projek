import { Link } from 'react-router-dom';
import { Badge } from '../ui';
import styles from './CourseCard.module.css';

export default function CourseCard({ course, isTeacher }) {
  return <Link to={'/course/' + course.id} className={styles.courseCard}>
    <div className={styles.courseCardHeader}><span className={styles.courseCode}>{course.shortname}</span><span className={styles.courseName}>{course.fullname}</span>{course.coursecategory && <span className={styles.courseMeta}>{course.coursecategory}</span>}</div>
    <div className={styles.courseCardFooter}>{isTeacher ? <Badge tone="info">Dosen</Badge> : <Badge tone="success">Mahasiswa</Badge>}<span className={styles.courseMeta}>Buka kursus →</span></div>
    {!isTeacher && course.hasprogress && course.progress != null && <div>
      <div className="h-1.5 overflow-hidden rounded-full bg-line"><div className="h-full bg-primary" style={{ width: course.progress + '%' }} /></div>
      <span className={styles.courseMeta}>{Math.round(course.progress)}% selesai</span>
    </div>}
  </Link>;
}
