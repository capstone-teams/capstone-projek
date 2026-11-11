import { Link, useOutletContext, useSearchParams } from 'react-router-dom';
import { useApi } from '../../../hooks/useApi';
import { usePolling } from '../../../hooks/usePolling';
import { listRps } from '../../../services/rpsService';
import { listWorkflows } from '../../../services/workflowService';
import { STAGE_LABELS, isWorkflowFinished } from '../../../utils/workflowStatus';
import { latestWorkflowPerRps } from '../../../utils/workflowList';

// Keterangan di bawah nama RPS: tahap berjalan, atau hasil akhir untuk workflow yang sudah berhenti.
const stageText = (workflow) => STAGE_LABELS[workflow.stage] ?? ({ COMPLETED: 'Selesai diproses', FAILED: 'Berhenti karena kesalahan' }[workflow.status] ?? 'Menunggu');
import { formatDateTime } from '../../../utils/format';
import { Card, EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import WorkflowDetail from '../../../components/ai/WorkflowDetail';
import WorkflowStatusBadge from '../../../components/ai/WorkflowStatusBadge';

const POLL_MS = 5000;

/**
 * Status workflow milik dosen (FE-10.1): daftar dari GET /workflows di kiri, detail tahap dan riwayat event workflow
 * terpilih di kanan. Di Generator AI sebuah kursus, daftar hanya berisi workflow kursus itu (satu kursus satu
 * workflow; RPS baru di kursus itu menggantikannya), yaitu workflow yang dipakai layout kursus. Di luar konteks kursus,
 * daftar berisi satu workflow terbaru per RPS. Tautan ke workflow lain tetap membuka detailnya.
 */
export default function WorkflowStatusPage() {
  const [params] = useSearchParams();
  // Konteks Generator AI kursus (AiCourseLayout): workflow aktif kursus ini.
  const courseContext = useOutletContext();
  const inCourse = !!courseContext?.course;
  const courseWorkflowId = courseContext?.workflowId ?? null;
  const courseWorkflowLoading = inCourse && !!courseContext?.workflowLoading;
  // Nama berkas RPS hanya pelengkap; kegagalannya tidak menghalangi daftar.
  const { data, error, loading, reload } = useApi(async () => {
    const [items, rps] = await Promise.all([listWorkflows(), listRps().then((result) => result.items).catch(() => [])]);
    return { items, rpsNames: new Map(rps.map((item) => [item.id, item.filename])) };
  });
  const items = data?.items ?? [];
  usePolling(() => reload({ silent: true }), POLL_MS, items.some((workflow) => !isWorkflowFinished(workflow)));

  if ((loading && !data) || courseWorkflowLoading) return <Spinner label="Memuat daftar workflow…" />;
  if (error && !data) return <ErrorAlert error={error} />;
  const visible = inCourse ? items.filter((workflow) => workflow.id === courseWorkflowId) : latestWorkflowPerRps(items);
  const requested = items.some((workflow) => workflow.id === params.get('workflow')) ? params.get('workflow') : null;
  if (!visible.length && !requested) {
    return (
      <EmptyState title={inCourse ? 'Kursus ini belum punya workflow.' : 'Belum ada workflow.'}>
        Workflow dibuat saat RPS diunggah dan diproses di tab RPS.
      </EmptyState>
    );
  }
  const selectedId = requested ?? visible[0].id;
  const rpsName = (workflow) => data.rpsNames.get(workflow.rps_id);

  return (
    <div className="grid grid--2">
      <Card title={inCourse ? 'Workflow kursus ini' : 'Workflow Anda'}>
        <ErrorAlert error={error} />
        <ul className="m-0 flex max-h-[70vh] list-none flex-col gap-2 overflow-y-auto p-0 pr-1" aria-label="Daftar workflow">
          {visible.map((workflow) => (
            <li key={workflow.id}>
              <Link
                to={`?workflow=${workflow.id}`}
                aria-current={workflow.id === selectedId ? 'true' : undefined}
                className={`flex flex-col gap-1.5 rounded-lg border p-3 text-ink no-underline hover:bg-surface ${workflow.id === selectedId ? 'border-primary bg-primary-light' : 'border-line'}`}
              >
                <span className="flex items-start justify-between gap-2">
                  <span className="min-w-0 font-semibold wrap-anywhere">{rpsName(workflow) ?? 'RPS'}</span>
                  <WorkflowStatusBadge workflow={workflow} />
                </span>
                <span className="text-sm text-muted">
                  {stageText(workflow)}
                  {workflow.progress?.total > 0 && ` · ${workflow.progress.completed}/${workflow.progress.total}`}
                  {' · '}{formatDateTime(workflow.created_at)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </Card>
      {/* Halaman ini berada di /course/{id}/ai/workflows: ".." menuju tab Generator AI lain (Rencana, Publikasi). */}
      <WorkflowDetail
        key={selectedId}
        workflowId={selectedId}
        rpsName={rpsName(items.find((workflow) => workflow.id === selectedId))}
        onChanged={() => reload({ silent: true })}
        linkBase=".."
      />
    </div>
  );
}
