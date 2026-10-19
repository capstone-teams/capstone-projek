import { useContext, useState } from 'react';
import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { approvePlan, generatePlan, getPlan, regeneratePlan } from '../../../services/courseService';
import { nullOn404 } from '../../../services/apiClient';
import { useAction, useApi } from '../../../hooks/useApi';
import { AppStateContext } from '../../../context/appStateContext';
import { Alert, Badge, Card, EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import InstructionModal from '../../../components/ai/InstructionModal';
import CoursePlanDetails from '../../../components/ai/course/CoursePlanDetails';

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
  const notify = useContext(AppStateContext)?.notify;
  const [revising, setRevising] = useState(false);
  // Versi rencana saat regenerasi diminta; dipakai untuk mengenali versi baru yang sudah siap.
  const [regenFrom, setRegenFrom] = useState(null);

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
  const approved = data?.status === 'approved';
  const regenerated = regenFrom != null && reviewing && (data?.version ?? 0) > regenFrom;

  const onApprove = () =>
    approve
      .run()
      .then(() => {
        setRegenFrom(null);
        notify?.('Rencana course disetujui.', { type: 'success' });
        return refresh();
      })
      .catch(() => {});

  const onRegenerate = (instruction) =>
    regeneratePlan(course.id, instruction).then(() => {
      setRegenFrom(data?.version ?? 0);
      notify?.('Instruksi regenerasi terkirim. Agent menyusun versi baru.');
      return refresh();
    });

  return (
    <Card
      title={data?.version != null ? `Rencana course · versi ${data.version}` : 'Rencana course'}
      actions={
        data && (
          <>
            <Badge tone={status.tone}>{status.label}</Badge>
            {reviewing && (
              <>
                <button type="button" className="btn btn--ghost" disabled={approve.pending} onClick={() => setRevising(true)}>
                  Minta revisi
                </button>
                <button type="button" className="btn btn--primary" disabled={approve.pending} onClick={onApprove}>
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
      {planning && (
        <Alert tone="info" title={`Agent sedang menyusun rencana${data ? ' versi baru' : ''}…`}>
          {data && 'Rencana di bawah adalah versi sebelumnya dan akan diganti otomatis setelah versi baru siap.'}
        </Alert>
      )}
      {regenerated && (
        <Alert tone="success" title={`Rencana versi ${data.version} siap direview`} onClose={() => setRegenFrom(null)}>
          Rencana sudah disusun ulang sesuai instruksi Anda. Periksa kembali sebelum menyetujui.
        </Alert>
      )}
      {approved && (
        <Alert tone="success" title="Rencana course telah disetujui">
          Lanjutkan dengan membuat konten mingguan berdasarkan rencana ini.{' '}
          <Link to="../content" relative="path" className="font-semibold underline">
            Buka tab konten
          </Link>
        </Alert>
      )}
      {data?.instruction && <Alert tone="info" title="Instruksi revisi terakhir">{data.instruction}</Alert>}
      {reviewing && data && !regenerated && (
        <p className="mb-4 text-muted">
          Tinjau rencana mingguan di bawah. Setujui bila sudah sesuai, atau minta revisi dengan instruksi perbaikan agar agent
          menyusun versi baru.
        </p>
      )}

      {plan.loading && data && <Spinner label="Memuat ulang rencana…" />}
      {plan.loading && !data ? (
        <Spinner />
      ) : !data ? (
        plan.error ? null : planning ? <Spinner label="Menyusun rencana…" /> : <EmptyState title="Rencana tidak ditemukan." />
      ) : (
        <div aria-busy={planning} className={planning ? 'opacity-60' : undefined}>
          <CoursePlanDetails plan={data} course={course} />
        </div>
      )}

      <InstructionModal
        open={revising}
        title="Minta revisi rencana"
        label="Instruksi perbaikan"
        hint="Sebutkan minggu dan bagian yang perlu diubah. Rencana saat ini tetap tersimpan sampai versi baru selesai."
        placeholder="Contoh: Perbaiki pembagian materi minggu 5-8"
        submitLabel="Regenerasi rencana"
        onClose={() => setRevising(false)}
        onSubmit={onRegenerate}
      />
    </Card>
  );
}
