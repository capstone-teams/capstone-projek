import { Link, useSearchParams } from 'react-router-dom';
import { useApi } from '../../../hooks/useApi';
import { usePolling } from '../../../hooks/usePolling';
import { listRps } from '../../../services/rpsService';
import { listWorkflows } from '../../../services/workflowService';
import { STAGE_LABELS, isWorkflowFinished } from '../../../utils/workflowStatus';

// Keterangan di bawah nama RPS: tahap berjalan, atau hasil akhir untuk workflow yang sudah berhenti.
const stageText = (workflow) => STAGE_LABELS[workflow.stage] ?? ({ COMPLETED: 'Selesai diproses', FAILED: 'Berhenti karena kesalahan' }[workflow.status] ?? 'Menunggu');
import { formatDateTime } from '../../../utils/format';
import { Card, EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import WorkflowDetail from '../../../components/ai/WorkflowDetail';
import WorkflowStatusBadge from '../../../components/ai/WorkflowStatusBadge';

const POLL_MS = 5000;

/**
 * Status workflow milik dosen (FE-10.1): daftar dari GET /workflows di kiri, detail tahap dan riwayat
 * event workflow terpilih di kanan. Workflow dipilih lewat ?workflow=<id>; tanpa itu yang terbaru.
 */
export default function WorkflowStatusPage() {
  const [params] = useSearchParams();
  // Nama berkas RPS hanya pelengkap; kegagalannya tidak menghalangi daftar.
  const { data, error, loading, reload } = useApi(async () => {
    const [items, rps] = await Promise.all([listWorkflows(), listRps().then((result) => result.items).catch(() => [])]);
    return { items, rpsNames: new Map(rps.map((item) => [item.id, item.filename])) };
  });
  const items = data?.items ?? [];
  usePolling(() => reload({ silent: true }), POLL_MS, items.some((workflow) => !isWorkflowFinished(workflow)));

  if (loading && !data) return <Spinner label="Memuat daftar workflow…" />;
  if (error && !data) return <ErrorAlert error={error} />;
  if (!items.length) {
    return <EmptyState title="Belum ada workflow.">Workflow dibuat saat RPS diunggah dan diproses di tab Ringkasan.</EmptyState>;
  }

  const selectedId = items.some((workflow) => workflow.id === params.get('workflow')) ? params.get('workflow') : items[0].id;
  const rpsName = (workflow) => data.rpsNames.get(workflow.rps_id);

  return (
    <div className="grid grid--2">
      <Card title="Workflow Anda">
        <ErrorAlert error={error} />
        <ul className="m-0 flex max-h-[70vh] list-none flex-col gap-2 overflow-y-auto p-0 pr-1" aria-label="Daftar workflow">
          {items.map((workflow) => (
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
