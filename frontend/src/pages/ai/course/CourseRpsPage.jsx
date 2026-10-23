import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { getRps, getRpsAnalysis } from '../../../services/rpsService';
import { useApi } from '../../../hooks/useApi';
import { Card, ErrorAlert, Spinner } from '../../../components/ui';
import RpsStatusBadge from '../../../components/ai/RpsStatusBadge';

/** Hasil analisis RPS yang dipakai project generator kursus ini. */
export default function CourseRpsPage() {
  const { course } = useCourse();
  const rpsId = course.rps_id;
  const { data, error, loading } = useApi(
    () => Promise.all([getRps(rpsId), getRpsAnalysis(rpsId)]).then(([rps, analysis]) => ({ rps, analysis })),
    [rpsId],
  );

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;

  const { rps, analysis } = data;
  return (
    <div className="stack">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex flex-wrap items-center gap-2 text-muted">
          {analysis.course.code} — {analysis.course.name} · {analysis.course.credits} SKS · {rps.filename}
          <RpsStatusBadge status={rps.status} />
        </p>
        {/* Monitoring workflow kursus ini ada di tab Ringkasan (Aktivitas agent). */}
        <Link to=".." relative="path" className="btn btn--ghost btn--sm">
          Pantau workflow
        </Link>
      </div>

      <div className="grid grid--2">
        <Card title="Capaian pembelajaran">
          <ul className="list">
            {analysis.learning_outcomes.map((lo) => (
              <li key={lo.code}>
                <strong>{lo.code}</strong> {lo.description}
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Komponen penilaian">
          <ul className="list">
            {analysis.assessment.map((a) => (
              <li key={a.component} className="list__split">
                <span>{a.component}</span>
                <strong>{a.weight}%</strong>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Rencana mingguan dari RPS">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Minggu</th>
                <th>Topik</th>
                <th>CPMK</th>
                <th>Metode</th>
              </tr>
            </thead>
            <tbody>
              {analysis.weekly_plan.map((w) => (
                <tr key={w.week}>
                  <td>{w.week}</td>
                  <td>{w.topic}</td>
                  <td>{w.cpmk?.join(', ')}</td>
                  <td>{w.method}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Referensi">
        <ul className="list">
          {analysis.references.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
