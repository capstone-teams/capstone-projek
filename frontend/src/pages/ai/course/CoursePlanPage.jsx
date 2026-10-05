import { useState } from 'react';
import { useCourse } from '../../../hooks/useCourse';
import { approvePlan, generatePlan, getPlan, regeneratePlan } from '../../../services/courseService';
import { nullOn404 } from '../../../services/apiClient';
import { useAction, useApi } from '../../../hooks/useApi';
import { Alert, Badge, Card, EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import InstructionModal from '../../../components/InstructionModal';
import CoursePlanDetails from '../../../components/course-plan/CoursePlanDetails';

const PLAN_STATUS = {
  draft: { label: 'Draft', tone: 'warning' },
  approved: { label: 'Disetujui', tone: 'success' },
  rejected: { label: 'Perlu revisi', tone: 'danger' },
};

export default function CoursePlanPage() {
  const { course, version, refresh } = useCourse();
  const hasPlan = course.status !== 'CREATED';
  const plan = useApi(() => (hasPlan ? getPlan(course.id).catch(nullOn404) : null), [course.id, version, hasPlan]);
  const generate = useAction(() => generatePlan(course.id), { loadingLabel: 'Meminta pembuatan rencana…' });
  const approve = useAction(() => approvePlan(course.id), { loadingLabel: 'Menyetujui rencana…' });
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
  const status = PLAN_STATUS[data?.status] ?? { label: data?.status || 'Status belum tersedia', tone: 'neutral' };
  return (
    <Card
      title={data?.version != null ? `Rencana course · versi ${data.version}` : 'Rencana course'}
      actions={
        data && (
          <>
            <Badge tone={status.tone}>{status.label}</Badge>
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
      <ErrorAlert error={actionError} onClose={() => {
          generate.clearError();
          approve.clearError();
        }} />
      {plan.error && (
        <div className="mb-4">
          <ErrorAlert error={plan.error} />
          <button type="button" className="btn" disabled={plan.loading} onClick={() => plan.reload()}>
            {plan.loading ? 'Memuat…' : 'Coba lagi'}
          </button>
        </div>
      )}
      {planning && <Alert tone="info">Agent sedang menyusun rencana{data ? ' versi baru' : ''}…</Alert>}
      {data?.instruction && <Alert tone="info" title="Instruksi revisi terakhir">{data.instruction}</Alert>}

      {plan.loading && data && <Spinner label="Memuat ulang rencana…" />}
      {plan.loading && !data ? (
        <Spinner />
      ) : !data ? (
        plan.error ? null : planning ? <Spinner label="Menyusun rencana…" /> : <EmptyState title="Rencana tidak ditemukan." />
      ) : (
        <CoursePlanDetails plan={data} course={course} />
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
