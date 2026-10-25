import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { getRps, getRpsAnalysis } from '../../../services/rpsService';
import { USE_MOCK } from '../../../services/config';
import { useApi } from '../../../hooks/useApi';
import { ErrorAlert, Spinner } from '../../../components/ui';
import RpsStatusBadge from '../../../components/ai/RpsStatusBadge';
import RpsAnalysisDetails from '../../../components/ai/course/RpsAnalysisDetails';
import { normalizeRpsAnalysis } from '../../../utils/rpsAnalysis';
import { formatDateTime } from '../../../utils/format';

// Course planning (FE-05) baru tersedia di backend pada M03; di mode mock sudah dapat dicoba.
const COURSE_PLANNING_AVAILABLE = USE_MOCK;

/** Hasil Analisis RPS (FE-08.3): diperiksa dosen sebelum melanjutkan ke course planning. */
export default function CourseRpsPage() {
  const { course } = useCourse();
  const rpsId = course.rps_id;
  const { data, error, loading, reload } = useApi(
    () => Promise.all([getRps(rpsId), getRpsAnalysis(rpsId)]).then(([rps, analysis]) => ({ rps, analysis })),
    [rpsId],
  );
  const analysis = useMemo(() => (data ? normalizeRpsAnalysis(data.analysis) : null), [data]);

  if (loading && !data) return <Spinner label="Memuat hasil analisis…" />;
  if (error) {
    return (
      <div>
        <ErrorAlert error={error} />
        <button type="button" className="btn" onClick={() => reload()}>Coba lagi</button>
      </div>
    );
  }

  const { rps } = data;
  return (
    <div className="stack">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl">Hasil analisis RPS</h2>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted">
            <span className="wrap-anywhere">{rps.filename}</span>
            <RpsStatusBadge status={rps.status} />
            {analysis.analyzedAt && <span>Dianalisis {formatDateTime(analysis.analyzedAt)}</span>}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* Monitoring workflow kursus ini ada di tab Ringkasan (Aktivitas agent). */}
          <Link to=".." relative="path" className="btn btn--ghost btn--sm">
            Pantau workflow
          </Link>
          {COURSE_PLANNING_AVAILABLE ? (
            <Link to="../plan" relative="path" className="btn btn--primary">
              Lanjut ke Course Planning
            </Link>
          ) : (
            <span className="flex flex-col items-end gap-1">
              <button type="button" className="btn btn--primary" disabled aria-describedby="planning-hint">
                Lanjut ke Course Planning
              </button>
              <span id="planning-hint" className="text-xs text-muted">Course planning aktif pada M03.</span>
            </span>
          )}
        </div>
      </div>

      <RpsAnalysisDetails analysis={analysis} />
    </div>
  );
}
