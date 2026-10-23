import { getRpsAnalysis } from '../../services/rpsService';
import { useApi } from '../../hooks/useApi';
import { ErrorAlert, Spinner } from '../ui';

/** Ringkasan hasil analisis satu RPS (GET /rps/{id}/analysis), untuk pratinjau sebelum project dibuat. */
export default function RpsAnalysisSummary({ rpsId }) {
  const { data, error, loading } = useApi(() => getRpsAnalysis(rpsId), [rpsId]);
  if (loading && !data) return <Spinner label="Memuat hasil analisis…" />;
  if (error) return <ErrorAlert error={error} />;

  // Bentuk §6.4 ({ data: RPS Structured Data }) maupun bentuk lama tanpa amplop `data`.
  const result = data?.data ?? data ?? {};
  const course = result.course ?? {};
  const outcomes = result.cpmk ?? result.learning_outcomes ?? [];
  const weeks = result.weeks ?? result.weekly_plan ?? [];
  const assessments = result.assessments ?? result.assessment ?? [];

  return (
    <dl className="mt-2 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 rounded-md bg-surface p-3 text-sm" aria-label="Ringkasan hasil analisis">
      <dt className="text-muted">Mata kuliah</dt>
      <dd>{[course.code, course.name].filter(Boolean).join(' — ') || '-'}{course.credits != null && ` · ${course.credits} SKS`}</dd>
      <dt className="text-muted">CPMK</dt>
      <dd>{outcomes.length} capaian</dd>
      <dt className="text-muted">Rencana</dt>
      <dd>{weeks.length} minggu</dd>
      <dt className="text-muted">Penilaian</dt>
      <dd>{assessments.length} komponen</dd>
    </dl>
  );
}
