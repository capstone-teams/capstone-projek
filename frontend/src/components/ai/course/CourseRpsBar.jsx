import { Link } from 'react-router-dom';
import { useApi } from '../../../hooks/useApi';
import { findCourseByMoodleId } from '../../../services/courseService';
import { getRps } from '../../../services/rpsService';
import { getActiveCourseBinding } from '../../../services/workflowService';
import { RPS_STATUS, rpsStatusMeta } from '../../../utils/rpsStatus';
import RpsStatusBadge from '../RpsStatusBadge';
import ActivityIcon from '../../moodle/ActivityIcon';
import { COURSE_CARD } from '../../moodle/course/courseCard';

/**
 * Kartu teratas tab Kursus untuk dosen, bergaya kartu aktivitas LMS ITK: RPS kursus ini (GET /rps/{id}) dengan
 * tautan ke halaman RPS dan ke hasil analisisnya di Generator AI. RPS diambil dari kursus backend (rps_id), atau dari project kursus bila halaman
 * berisi data kursus tanpa rps_id. Backend belum menyediakan unduhan berkas RPS, jadi tautan membuka detailnya.
 */
export default function CourseRpsBar({ course }) {
  const courseKeys = [course?.id, course?.moodle_course_id, course?.shortname, course?.code].filter(Boolean);
  const bound = getActiveCourseBinding(...courseKeys);
  const boundRpsId = bound?.rpsId;

  const { data, loading } = useApi(async () => {
    const rpsId = boundRpsId ?? course?.rps_id ?? (await findCourseByMoodleId(course?.id).catch(() => null))?.rps_id;
    return rpsId ? getRps(rpsId).catch(() => ({ id: rpsId })) : null;
  }, [course?.id, course?.rps_id, boundRpsId]);

  if (loading) return null;
  const base = `/course/${course.id}/ai`;

  if (!data) {
    return (
      <div className={`${COURSE_CARD} flex flex-wrap items-center gap-3`} aria-label="RPS kursus">
        <ActivityIcon modname="resource" boxed />
        <span className="min-w-0 flex-1 text-sm text-muted">Kursus ini belum memiliki RPS.</span>
        <Link to={base} className="btn btn--ghost btn--sm">Unggah RPS</Link>
      </div>
    );
  }

  const analyzed = data.status === RPS_STATUS.ANALYZED;
  const rpsPath = `${base}/rps?rps=${encodeURIComponent(data.id)}`;
  return (
    <div className={`${COURSE_CARD} flex flex-wrap items-center gap-3`} aria-label="RPS kursus">
      <ActivityIcon modname="resource" boxed />
      <div className="min-w-0 flex-1">
        <Link to={rpsPath} className="font-semibold">Rencana Pembelajaran Semester (RPS)</Link>
        <div className="mt-0.5 flex flex-wrap items-center gap-2 text-sm text-muted">
          <span className="wrap-anywhere">{data.filename ?? 'RPS'}</span>
          {data.status && <RpsStatusBadge status={data.status} />}
        </div>
      </div>
      {analyzed ? (
        <Link to={`${rpsPath}&bagian=hasil`} className="btn btn--ghost btn--sm">Hasil analisis</Link>
      ) : (
        <button type="button" className="btn btn--ghost btn--sm" disabled title={rpsStatusMeta(data.status).description}>
          Hasil analisis
        </button>
      )}
    </div>
  );
}
