import { useContext, useState } from 'react';
import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { getPlan } from '../../../services/courseService';
import {
  MAX_PLAN_NOTE_LENGTH,
  PLAN_STATUS,
  PLAN_STATUS_META,
  approveWorkflowPlan,
  generateWorkflowPlan,
  getWorkflowPlan,
  getWorkflowPlanVersion,
  listWorkflowPlanVersions,
  regenerateWorkflowPlan,
  rejectWorkflowPlan,
} from '../../../services/coursePlanService';
import { getRps } from '../../../services/rpsService';
import { nullOn404 } from '../../../services/apiClient';
import { useAction, useApi } from '../../../hooks/useApi';
import { useOnChange } from '../../../hooks/useOnChange';
import { AppStateContext } from '../../../context/appStateContext';
import { Alert, Badge, Card, EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import InstructionModal from '../../../components/ai/InstructionModal';
import CoursePlanDetails from '../../../components/ai/course/CoursePlanDetails';
import { RPS_STATUS } from '../../../utils/rpsStatus';
import { WORKFLOW_API_STATUS, WORKFLOW_STAGE, needsInstructorAction } from '../../../utils/workflowStatus';
import { formatDateTime } from '../../../utils/format';

const statusMeta = (status) => PLAN_STATUS_META[status] ?? { label: status || 'Status belum tersedia', tone: 'neutral' };

/** Daftar versi course plan (GET /plan/versions); memilih versi lama menampilkannya tanpa aksi review. */
function PlanVersions({ versions, selected, latest, onSelect }) {
  if (versions.length < 2) return null;
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 text-sm" role="group" aria-label="Versi rencana">
      <span className="text-muted">Versi:</span>
      {[...versions].sort((a, b) => b.version - a.version).map((item) => {
        const active = (selected ?? latest) === item.version;
        return (
          <button
            key={item.version}
            type="button"
            aria-pressed={active}
            className={`btn btn--sm ${active ? 'btn--primary' : 'btn--ghost'}`}
            title={`${statusMeta(item.status).label}${item.created_at ? ` · ${formatDateTime(item.created_at)}` : ''}`}
            onClick={() => onSelect(item.version === latest ? null : item.version)}
          >
            v{item.version}{item.version === latest ? ' (terbaru)' : ''}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Rencana course (FE-05) lewat API course plan per workflow (BE-14): generate, approve, reject dengan catatan,
 * regenerate dengan prompt tambahan, dan riwayat versi. Tanpa course plan di workflow, rencana project kursus
 * (GET /courses/{id}/plan) ditampilkan sebagai bacaan.
 */
export default function CoursePlanPage() {
  const { course, workflow, workflowId, refresh } = useCourse();
  const notify = useContext(AppStateContext)?.notify;
  const [dialog, setDialog] = useState(null); // 'reject' | 'regenerate'
  const [selectedVersion, setSelectedVersion] = useState(null);

  const plan = useApi(() => (workflowId ? getWorkflowPlan(workflowId) : null), [workflowId]);
  const versions = useApi(() => (workflowId ? listWorkflowPlanVersions(workflowId).catch(() => []) : []), [workflowId]);
  const older = useApi(() => (workflowId && selectedVersion ? getWorkflowPlanVersion(workflowId, selectedVersion) : null), [workflowId, selectedVersion]);
  // Tanpa course plan workflow: rencana project kursus (bacaan) dan status RPS untuk syarat generate.
  // Tanpa workflow, atau workflow belum punya course plan: rencana project kursus tampil sebagai bacaan.
  const planMissing = !workflowId || (!plan.loading && !plan.error && plan.data === null);
  const projectPlan = useApi(() => (planMissing && course.id ? getPlan(course.id).catch(nullOn404) : null), [planMissing, course.id]);
  const rpsId = workflow?.rps_id ?? course.rps_id;
  const rps = useApi(() => (rpsId ? getRps(rpsId).catch(() => null) : null), [rpsId]);

  // Workflow diperbarui real-time (FE-10.2): rencana dimuat ulang setiap status atau tahapnya berubah.
  const workflowChange = workflow ? `${workflow.status}|${workflow.stage}|${workflow.updated_at}` : null;
  const { reload: reloadPlan } = plan;
  const { reload: reloadVersions } = versions;
  useOnChange(workflowChange, () => {
    reloadPlan({ silent: true });
    reloadVersions({ silent: true });
  }, 300);

  const after = (message) => () => {
    if (message) notify?.(message, { type: 'success' });
    setSelectedVersion(null);
    reloadPlan({ silent: true });
    reloadVersions({ silent: true });
    refresh?.();
  };
  const generate = useAction(() => generateWorkflowPlan(workflowId), { loadingLabel: 'Meminta penyusunan rencana…' });
  const approve = useAction(() => approveWorkflowPlan(workflowId), { loadingLabel: 'Menyetujui rencana…' });

  const planning = workflow?.status === WORKFLOW_API_STATUS.RUNNING && workflow?.stage === WORKFLOW_STAGE.COURSE_PLANNING;
  const latest = plan.data;
  const shown = selectedVersion ? older.data : latest;
  const viewingOld = !!selectedVersion;
  const rpsReady = rps.data?.status === RPS_STATUS.ANALYZED;
  const reviewable = !viewingOld && latest?.status === PLAN_STATUS.DRAFT;
  const waitingReview = needsInstructorAction(workflow);
  const actionError = generate.error || approve.error;

  if (workflowId && plan.loading && latest === null && !plan.error) return <Spinner label="Memuat rencana…" />;

  if (!latest) {
    const readOnly = projectPlan.data;
    const readOnlyMeta = statusMeta(readOnly?.status);
    return (
      <Card
        title={readOnly?.version != null ? `Rencana course · versi ${readOnly.version}` : 'Rencana course'}
        actions={readOnly?.status && <Badge tone={readOnlyMeta.tone}>{readOnlyMeta.label}</Badge>}
      >
        <ErrorAlert error={plan.error ?? generate.error} onClose={generate.clearError} />
        {plan.error && (
          <button type="button" className="btn mb-4" disabled={plan.loading} onClick={() => plan.reload()}>
            {plan.loading ? 'Memuat…' : 'Coba lagi'}
          </button>
        )}
        {!workflowId ? (
          <p className="mb-4 text-sm text-muted">Generate rencana tersedia setelah RPS kursus ini diproses dan dianalisis di tab RPS.</p>
        ) : planning ? (
          <Alert tone="info" title="Agent sedang menyusun rencana…">Rencana tampil otomatis setelah selesai disusun.</Alert>
        ) : (
          !plan.error && (
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="btn btn--primary"
                disabled={!rpsReady || generate.pending}
                onClick={() => generate.run().then(after('Penyusunan rencana dimulai.')).catch(() => {})}
              >
                {generate.pending ? 'Meminta…' : 'Generate rencana'}
              </button>
              <span className="text-sm text-muted">
                {rpsReady
                  ? 'Agent menyusun rencana mingguan dari hasil analisis RPS dan setup dosen.'
                  : 'Tersedia setelah RPS kursus ini selesai dianalisis.'}
              </span>
            </div>
          )
        )}
        {readOnly ? (
          <>
            <p className="mb-3 text-sm text-muted">Rencana tersimpan pada project kursus (hanya dibaca).</p>
            <CoursePlanDetails plan={readOnly} course={course} />
          </>
        ) : projectPlan.loading ? (
          <Spinner label="Memuat rencana…" />
        ) : (
          !planning && <EmptyState title="Rencana belum dibuat." />
        )}
      </Card>
    );
  }

  const meta = statusMeta(shown?.status);
  return (
    <Card
      title={shown?.version != null ? `Rencana course · versi ${shown.version}` : 'Rencana course'}
      actions={
        shown && (
          <>
            <Badge tone={meta.tone}>{meta.label}</Badge>
            {reviewable && (
              <>
                <button type="button" className="btn btn--ghost" disabled={!waitingReview || approve.pending} onClick={() => setDialog('reject')}>
                  Tolak dengan catatan
                </button>
                <button
                  type="button"
                  className="btn btn--primary"
                  disabled={!waitingReview || approve.pending || latest.validation?.passed === false}
                  onClick={() => approve.run().then(after('Rencana course disetujui.')).catch(() => {})}
                >
                  {approve.pending ? 'Menyimpan…' : 'Setujui rencana'}
                </button>
              </>
            )}
            {!viewingOld && latest.status === PLAN_STATUS.REJECTED && (
              <button type="button" className="btn btn--primary" disabled={planning} onClick={() => setDialog('regenerate')}>
                Regenerasi rencana
              </button>
            )}
          </>
        )
      }
    >
      <ErrorAlert error={actionError} onClose={() => { generate.clearError(); approve.clearError(); }} />
      <ErrorAlert error={plan.error} />
      <PlanVersions versions={versions.data ?? []} selected={selectedVersion} latest={latest.version} onSelect={setSelectedVersion} />
      {viewingOld && (
        <Alert tone="info" title={`Menampilkan versi ${selectedVersion}`}>
          Versi lama hanya untuk ditinjau.{' '}
          <button type="button" className="font-semibold underline" onClick={() => setSelectedVersion(null)}>Kembali ke versi terbaru</button>
        </Alert>
      )}
      {planning && <Alert tone="info" title="Agent sedang menyusun versi baru…">Rencana di bawah akan diganti otomatis setelah versi baru siap.</Alert>}
      {reviewable && !waitingReview && !planning && (
        <p className="mb-4 text-sm text-muted">Setujui atau tolak tersedia ketika workflow menunggu peninjauan Anda.</p>
      )}
      {reviewable && latest.validation?.passed === false && (
        <Alert tone="warning" title="Rencana belum lolos validasi">
          <ul className="m-0 list-disc pl-5">
            {(latest.validation.issues ?? []).map((issue, index) => (
              <li key={index}>{issue.message ?? JSON.stringify(issue)}</li>
            ))}
          </ul>
        </Alert>
      )}
      {latest.status === PLAN_STATUS.APPROVED && !viewingOld && (
        <Alert tone="success" title="Rencana course telah disetujui">
          Lanjutkan dengan konten mingguan berdasarkan rencana ini.{' '}
          <Link to="../content" relative="path" className="font-semibold underline">Buka tab konten</Link>
        </Alert>
      )}
      {shown?.revision_notes && <Alert tone="warning" title="Catatan revisi">{shown.revision_notes}</Alert>}
      {shown?.regeneration_instruction && <Alert tone="info" title="Prompt tambahan saat regenerasi">{shown.regeneration_instruction}</Alert>}

      {viewingOld && older.loading ? <Spinner /> : shown ? <CoursePlanDetails plan={shown} course={course} /> : null}
      <ErrorAlert error={older.error} />

      <InstructionModal
        open={dialog === 'reject'}
        title="Tolak rencana"
        label="Catatan revisi"
        hint="Jelaskan bagian yang perlu diperbaiki; catatan dipakai agent saat regenerasi."
        placeholder="Contoh: Pembagian materi minggu 5-8 terlalu padat."
        submitLabel="Tolak rencana"
        danger
        maxLength={MAX_PLAN_NOTE_LENGTH}
        onClose={() => setDialog(null)}
        onSubmit={(notes) => rejectWorkflowPlan(workflowId, notes).then(after('Rencana ditolak. Anda dapat meregenerasinya.'))}
      />
      <InstructionModal
        open={dialog === 'regenerate'}
        title="Regenerasi rencana"
        label="Prompt tambahan"
        hint="Opsional. Instruksi untuk agent saat menyusun versi baru, selain catatan revisi."
        placeholder="Contoh: Tambahkan studi kasus sistem informasi kampus pada setiap pertemuan praktikum."
        submitLabel="Regenerasi rencana"
        optional
        maxLength={MAX_PLAN_NOTE_LENGTH}
        onClose={() => setDialog(null)}
        onSubmit={(instruction) => regenerateWorkflowPlan(workflowId, instruction).then(after('Regenerasi rencana dimulai.'))}
      />
    </Card>
  );
}
