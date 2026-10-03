import { useState } from 'react';
import { useCourse } from '../../../hooks/useCourse';
import { approvePlan, generatePlan, getPlan, regeneratePlan } from '../../../services/courseService';
import { nullOn404 } from '../../../services/apiClient';
import { useAction, useApi } from '../../../hooks/useApi';
import { Alert, Badge, Card, EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import InstructionModal from '../../../components/InstructionModal';

const ACTIVITY_LABELS = { learning_material: 'Materi', assignment: 'Tugas', quiz: 'Kuis' };

export default function CoursePlanPage() {
  const { course, version, refresh } = useCourse();
  const hasPlan = course.status !== 'CREATED';
  const plan = useApi(() => (hasPlan ? getPlan(course.id).catch(nullOn404) : null), [course.id, version, hasPlan]);
  const generate = useAction(() => generatePlan(course.id));
  const approve = useAction(() => approvePlan(course.id));
  const [revising, setRevising] = useState(false);

  const reviewing = course.status === 'WAITING_PLAN_REVIEW';
  const planning = course.status === 'PLANNING';
  const actionError = generate.error || approve.error;

  if (course.status === 'CREATED') {
    return (
      <Card>
        <ErrorAlert error={generate.error} onClose={generate.clearError} />
        <EmptyState
          title="Rencana belum dibuat."
          action={
            <button
              type="button"
              className="btn btn--primary"
              disabled={generate.pending}
              onClick={() => generate.run().then(refresh).catch(() => {})}
            >
              {generate.pending ? 'Meminta…' : 'Generate rencana'}
            </button>
          }
        >
          Agent akan menyusun rencana mingguan berdasarkan RPS, profil dosen, dan prompt tambahan.
        </EmptyState>
      </Card>
    );
  }

  const data = plan.data;
  return (
    <Card
      title={data ? `Rencana course · versi ${data.version}` : 'Rencana course'}
      actions={
        data && (
          <>
            <Badge tone={data.status === 'approved' ? 'success' : 'warning'}>
              {data.status === 'approved' ? 'Disetujui' : 'Draft'}
            </Badge>
            {reviewing && (
              <>
                <button type="button" className="btn btn--ghost" onClick={() => setRevising(true)}>
                  Minta revisi
                </button>
                <button
                  type="button"
                  className="btn btn--primary"
                  disabled={approve.pending}
                  onClick={() => approve.run().then(refresh).catch(() => {})}
                >
                  {approve.pending ? 'Menyimpan…' : 'Setujui rencana'}
                </button>
              </>
            )}
          </>
        )
      }
    >
      <ErrorAlert error={actionError || plan.error} onClose={() => {
          generate.clearError();
          approve.clearError();
        }} />
      {planning && <Alert tone="info">Agent sedang menyusun rencana{data ? ' versi baru' : ''}…</Alert>}
      {data?.instruction && <Alert tone="info" title="Instruksi revisi terakhir">{data.instruction}</Alert>}

      {plan.loading && !data ? (
        <Spinner />
      ) : !data ? (
        planning ? <Spinner label="Menyusun rencana…" /> : <EmptyState title="Rencana tidak ditemukan." />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Minggu</th>
                <th>Topik</th>
                <th>Tujuan pembelajaran</th>
                <th>Aktivitas</th>
              </tr>
            </thead>
            <tbody>
              {data.weeks.map((w) => (
                <tr key={w.week}>
                  <td>{w.week}</td>
                  <td>
                    <strong>{w.topic}</strong>
                    {w.sub_topics?.length > 0 && <div className="muted">{w.sub_topics.join(' · ')}</div>}
                    {w.note && <div className="note">{w.note}</div>}
                  </td>
                  <td>
                    <ul className="compact">
                      {w.learning_objectives.map((o) => (
                        <li key={o}>{o}</li>
                      ))}
                    </ul>
                  </td>
                  <td>
                    <div className="chips">
                      {w.planned_activities?.map((a) => (
                        <Badge key={a}>{ACTIVITY_LABELS[a] ?? a}</Badge>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <InstructionModal
        open={revising}
        title="Minta revisi rencana"
        label="Instruksi perbaikan"
        placeholder="Contoh: Perbaiki pembagian materi minggu 5-8"
        submitLabel="Regenerasi rencana"
        onClose={() => setRevising(false)}
        onSubmit={(instruction) => regeneratePlan(course.id, instruction).then(refresh)}
      />
    </Card>
  );
}
