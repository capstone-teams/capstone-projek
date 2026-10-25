import { getRpsAnalysis } from '../../services/rpsService';
import { useApi } from '../../hooks/useApi';
import { normalizeRpsAnalysis } from '../../utils/rpsAnalysis';
import { ErrorAlert, Spinner } from '../ui';

/** Ringkasan hasil analisis di kartu RPS, selama project kursus belum dibuat. */
export default function RpsAnalysisSummary({ rpsId }) {
  const { data, error, loading } = useApi(() => getRpsAnalysis(rpsId).then(normalizeRpsAnalysis), [rpsId]);
  if (loading && !data) return <Spinner label="Memuat hasil analisis…" />;
  if (error) return <ErrorAlert error={error} />;

  const { course, cpmk, weeks, assessments } = data;
  return (
    <dl className="mt-2 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 rounded-md bg-surface p-3 text-sm" aria-label="Ringkasan hasil analisis">
      <dt className="text-muted">Mata kuliah</dt>
      <dd>{[course.code, course.name].filter(Boolean).join(' — ') || '-'}{course.credits != null && ` · ${course.credits} SKS`}</dd>
      <dt className="text-muted">CPMK</dt>
      <dd>{cpmk.length} capaian</dd>
      <dt className="text-muted">Rencana</dt>
      <dd>{weeks.length} minggu</dd>
      <dt className="text-muted">Penilaian</dt>
      <dd>{assessments.length} komponen</dd>
    </dl>
  );
}
