import { useContext, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { useWorkflowMonitor } from '../../../hooks/useWorkflowMonitor';
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
import { Alert, Badge, Card, EmptyState, ErrorAlert, Modal, Spinner } from '../../../components/ui';
import InstructionModal from '../../../components/ai/InstructionModal';
import CoursePlanDetails from '../../../components/ai/course/CoursePlanDetails';
import CoursePlanProgress from '../../../components/ai/course/CoursePlanProgress';
import CoursePlanValidation from '../../../components/ai/course/CoursePlanValidation';
import { RPS_STATUS } from '../../../utils/rpsStatus';
import { groupValidationIssues } from '../../../utils/coursePlan';
import { WORKFLOW_API_STATUS, coursePlanFailureOf, coursePlanProgressOf, needsInstructorAction } from '../../../utils/workflowStatus';
import { formatDateTime } from '../../../utils/format';

const statusMeta = (status) => PLAN_STATUS_META[status] ?? { label: status || 'Status belum tersedia', tone: 'neutral' };
const PLAN_FAILED_MESSAGE = 'Penyusunan rencana gagal. Silakan coba lagi.';

/**
 * Riwayat versi course plan (GET /plan/versions, terbaru di atas) dengan penanda status approval per versi.
 * Membuka versi lama menampilkannya tanpa aksi review (GET /plan/versions/{version}).
 */
function PlanHistory({ versions, selected, latest, onSelect }) {
  if (!versions.length) return null;
  return (
    <section className="mb-4 rounded-lg border border-line" aria-label="Riwayat versi">
      <h3 className="border-b border-line px-4 py-2.5 text-[15px] font-semibold">Riwayat versi</h3>
      <ol className="m-0 list-none divide-y divide-line p-0">
        {[...versions].sort((a, b) => b.version - a.version).map((item) => {
          const active = (selected ?? latest) === item.version;
          const meta = statusMeta(item.status);
          return (
            <li key={item.version} className={`flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5 ${active ? 'bg-primary-light/50' : ''}`} aria-label={`Versi ${item.version}`}>
              <span className="font-semibold">Versi {item.version}</span>
              {item.version === latest && <span className="text-xs text-muted">(terbaru)</span>}
              <Badge tone={meta.tone}>{meta.label}</Badge>
              <span className="text-sm text-muted">
                {item.created_at && `Dibuat ${formatDateTime(item.created_at)}`}
                {item.approved_at && ` · Disetujui ${formatDateTime(item.approved_at)}`}
              </span>
              <button
                type="button"
                className="btn btn--ghost btn--sm ml-auto"
                aria-pressed={active}
                disabled={active}
                onClick={() => onSelect(item.version === latest ? null : item.version)}
              >
                {active ? 'Sedang ditampilkan' : `Lihat versi ${item.version}`}
              </button>
              {item.revision_notes && <p className="w-full text-sm text-ink-subtle">Catatan revisi: {item.revision_notes}</p>}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

/** Kegagalan course planning (workflow FAILED) beserta jalan keluarnya: generate ulang atau regenerasi. */
function PlanFailure({ message, children }) {
  return (
    <Alert tone="danger" title="Penyusunan rencana gagal">
      <p>{message}</p>
      {children && <div className="mt-2 flex flex-wrap items-center gap-2">{children}</div>}
    </Alert>
  );
}

/**
 * Rencana course (FE-05, FE-12.1) lewat API course plan per workflow (BE-14):
 * - generate (POST /workflows/{id}/plan) lalu progres PLANNING_COURSE → VALIDATING (RETRYING bila dicoba ulang)
 *   dari event workflow real-time (FE-10.2); rencana dimuat ulang otomatis begitu workflow menunggu review;
 * - kegagalan (workflow FAILED) menampilkan pesannya dengan opsi generate ulang;
 * - approve, reject dengan catatan, regenerate dengan prompt tambahan, riwayat versi, dan hasil validasi.
 * Workflow berasal dari project kursus, atau dari ?workflow=<id> (dari halaman Hasil Analisis RPS). Tanpa course
 * plan di workflow, rencana project kursus (GET /courses/{id}/plan) ditampilkan sebagai bacaan.
 */
export default function CoursePlanPage() {
  const { course, workflow: projectWorkflow, workflowId: projectWorkflowId, events: projectEvents = [], refresh } = useCourse();
  const notify = useContext(AppStateContext)?.notify;
  const [dialog, setDialog] = useState(null); // 'approve' | 'reject' | 'regenerate'
  const [selectedVersion, setSelectedVersion] = useState(null);

  // Workflow lain lewat ?workflow= dipantau sendiri; workflow project sudah dipantau AiCourseLayout.
  const [params] = useSearchParams();
  const workflowParam = params.get('workflow');
  const ownWorkflowId = workflowParam && workflowParam !== projectWorkflowId ? workflowParam : null;
  const own = useWorkflowMonitor(ownWorkflowId);
  const workflowId = workflowParam || projectWorkflowId;
  const workflow = ownWorkflowId ? own.workflow : projectWorkflow;
  const events = ownWorkflowId ? own.events : projectEvents;

  const plan = useApi(() => (workflowId ? getWorkflowPlan(workflowId) : null), [workflowId]);
  const versions = useApi(() => (workflowId ? listWorkflowPlanVersions(workflowId).catch(() => []) : []), [workflowId]);
  const older = useApi(() => (workflowId && selectedVersion ? getWorkflowPlanVersion(workflowId, selectedVersion) : null), [workflowId, selectedVersion]);
  // Tanpa workflow, atau workflow belum punya course plan: rencana project kursus tampil sebagai bacaan.
  const planMissing = !workflowId || (!plan.loading && !plan.error && plan.data === null);
  const projectPlan = useApi(() => (planMissing && course?.id ? getPlan(course.id).catch(nullOn404) : null), [planMissing, course?.id]);
  const rpsId = workflow?.rps_id ?? course?.rps_id;
  const rps = useApi(() => (rpsId ? getRps(rpsId).catch(() => null) : null), [rpsId]);

  // Workflow diperbarui real-time (FE-10.2): rencana dimuat ulang setiap status atau tahapnya berubah, termasuk
  // saat versi baru tersimpan dan saat workflow masuk WAITING_FOR_REVIEW.
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
    own.reload();
  };
  const generate = useAction(() => generateWorkflowPlan(workflowId), { loadingLabel: 'Meminta penyusunan rencana…' });
  const approve = useAction(() => approveWorkflowPlan(workflowId), { loadingLabel: 'Menyetujui rencana…' });
  const startGenerate = () => generate.run().then(after('Penyusunan rencana dimulai.')).catch(() => {});
  // Approve setelah dikonfirmasi; galat ditampilkan di dialog agar dosen dapat mencoba lagi.
  const confirmApprove = () => approve.run().then(() => {
    setDialog(null);
    after('Rencana course disetujui.')();
  }).catch(() => {});

  const latest = plan.data;
  const progress = coursePlanProgressOf(workflow, events);
  const inProgress = !!progress;
  const rpsReady = rps.data?.status === RPS_STATUS.ANALYZED;
  // Kegagalan pada tahap course planning/validasi; tanpa riwayat event, workflow gagal setelah RPS selesai
  // dianalisis dan sebelum rencana pertama tersimpan juga berarti penyusunan rencana gagal.
  const failureEvent = coursePlanFailureOf(workflow, events);
  const planFailed = !inProgress && (!!failureEvent || (!latest && rpsReady && workflow?.status === WORKFLOW_API_STATUS.FAILED));
  const failureMessage = failureEvent?.message || PLAN_FAILED_MESSAGE;
  const shown = selectedVersion ? older.data : latest;
  const viewingOld = !!selectedVersion;
  const reviewable = !viewingOld && latest?.status === PLAN_STATUS.DRAFT;
  const waitingReview = needsInstructorAction(workflow);
  const validationPassed = latest?.validation?.passed === true;
  const issuesByWeek = useMemo(() => groupValidationIssues(shown?.validation?.issues ?? []).byWeek, [shown]);

  if (workflowId && plan.loading && latest === null && !plan.error) return <Spinner label="Memuat rencana…" />;

  if (!latest) {
    const showReadOnly = Boolean(projectPlan.data && (!workflowId || !rpsReady));
    const readOnly = showReadOnly ? projectPlan.data : null;
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
        ) : inProgress ? (
          <CoursePlanProgress progress={progress} events={events} />
        ) : planFailed && !plan.error ? (
          <PlanFailure message={failureMessage}>
            <button type="button" className="btn btn--primary" disabled={!rpsReady || generate.pending} onClick={startGenerate}>
              {generate.pending ? 'Meminta…' : 'Generate ulang'}
            </button>
          </PlanFailure>
        ) : (
          !plan.error && (
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <button type="button" className="btn btn--primary" disabled={!rpsReady || generate.pending} onClick={startGenerate}>
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
            <CoursePlanDetails plan={readOnly} course={course ?? {}} />
          </>
        ) : projectPlan.loading && !workflowId ? (
          <Spinner label="Memuat rencana…" />
        ) : (
          !inProgress && (
            <EmptyState
              title="Rencana belum dibuat."
              description={rpsReady ? 'Klik tombol "Generate rencana" di atas untuk menyusun rencana mingguan dari hasil analisis RPS.' : undefined}
            />
          )
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
                  disabled={!waitingReview || approve.pending || !validationPassed}
                  onClick={() => {
                    approve.clearError();
                    setDialog('approve');
                  }}
                >
                  Setujui rencana
                </button>
              </>
            )}
            {!viewingOld && latest.status === PLAN_STATUS.REJECTED && (
              <button type="button" className="btn btn--primary" disabled={inProgress} onClick={() => setDialog('regenerate')}>
                Regenerasi rencana
              </button>
            )}
          </>
        )
      }
    >
      <ErrorAlert error={generate.error} onClose={generate.clearError} />
      <ErrorAlert error={plan.error} />
      {inProgress && <CoursePlanProgress progress={progress} events={events} replacing />}
      {planFailed && (
        <PlanFailure message={failureMessage}>
          {latest.status === PLAN_STATUS.REJECTED ? (
            <button type="button" className="btn btn--primary" onClick={() => setDialog('regenerate')}>Generate ulang</button>
          ) : (
            <span className="text-sm">Tolak versi ini dengan catatan untuk menyusun ulang rencana.</span>
          )}
        </PlanFailure>
      )}
      <PlanHistory versions={versions.data ?? []} selected={selectedVersion} latest={latest.version} onSelect={setSelectedVersion} />
      {viewingOld && (
        <Alert tone="info" title={`Menampilkan versi ${selectedVersion}`}>
          Versi lama hanya untuk ditinjau.{' '}
          <button type="button" className="font-semibold underline" onClick={() => setSelectedVersion(null)}>Kembali ke versi terbaru</button>
        </Alert>
      )}
      {reviewable && !waitingReview && (
        <p className="mb-4 text-sm text-muted">Setujui atau tolak tersedia ketika workflow menunggu peninjauan Anda.</p>
      )}
      {shown?.validation && <CoursePlanValidation validation={shown.validation} />}
      {latest.status === PLAN_STATUS.APPROVED && !viewingOld && (
        <Alert tone="success" title="Rencana course telah disetujui">
          {latest.approved_at && <p>Disetujui {formatDateTime(latest.approved_at)}.</p>}
          <p>
            Langkah berikutnya: buat struktur mingguan rencana ini di kursus Moodle target.
            {course?.id && (
              <>
                {' '}<Link to="../publish" relative="path" className="font-semibold underline">Lanjut ke eksekusi struktur</Link>
              </>
            )}
          </p>
        </Alert>
      )}
      {shown?.revision_notes && <Alert tone="warning" title="Catatan revisi">{shown.revision_notes}</Alert>}
      {shown?.regeneration_instruction && <Alert tone="info" title="Prompt tambahan saat regenerasi">{shown.regeneration_instruction}</Alert>}

      {viewingOld && older.loading ? <Spinner /> : shown ? <CoursePlanDetails plan={shown} course={course ?? {}} issuesByWeek={issuesByWeek} /> : null}
      <ErrorAlert error={older.error} />

      <Modal
        open={dialog === 'approve'}
        title="Setujui rencana"
        onClose={() => !approve.pending && setDialog(null)}
        footer={(
          <>
            <button type="button" className="btn btn--ghost" disabled={approve.pending} onClick={() => setDialog(null)}>Batal</button>
            <button type="button" className="btn btn--primary" disabled={approve.pending} onClick={confirmApprove}>
              {approve.pending ? 'Menyimpan…' : 'Ya, setujui'}
            </button>
          </>
        )}
      >
        <ErrorAlert error={approve.error} onClose={approve.clearError} />
        <p>
          Versi {latest.version} akan disetujui sebagai rencana course. Rencana yang sudah disetujui tidak dapat ditolak
          maupun disetujui ulang, dan menjadi dasar struktur mingguan di kursus Moodle.
        </p>
      </Modal>
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
