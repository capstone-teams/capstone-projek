import { useApi } from '../../hooks/useApi';
import { useOnChange } from '../../hooks/useOnChange';
import {
  EXECUTION_STATUS_META,
  OPERATION_STATUS_META,
  OPERATION_TYPE_LABELS,
  getLatestWorkflowExecution,
} from '../../services/executionService';
import { WORKFLOW_EVENT, WORKFLOW_STAGE } from '../../utils/workflowStatus';
import { Badge, Card, ErrorAlert } from '../ui';

// Event operasi beruntun (satu per minggu) digabung menjadi satu GET detail eksekusi.
const REFRESH_DEBOUNCE_MS = 300;

const meta = (table, status) => table[status] ?? { label: status ?? '-', tone: 'neutral' };

/**
 * Detail event OPERASI_MOODLE (BE-17.1): jenis operasi, minggu, dan status setiap operasi eksekusi terbaru.
 * Payload event monitoring tidak membawa rincian operasi, jadi rinciannya dibaca dari
 * GET /workflows/{id}/executions/{execution_id} dan dimuat ulang setiap ada event eksekusi baru.
 */
export default function WorkflowMoodleOperations({ workflowId, events = [] }) {
  const executionEvents = events.filter((event) => event.event === WORKFLOW_EVENT.MOODLE_OPERATION || event.stage === WORKFLOW_STAGE.MOODLE_EXECUTION);
  const executed = executionEvents.length > 0;
  const execution = useApi(() => (executed ? getLatestWorkflowExecution(workflowId) : null), [workflowId, executed]);
  const { reload } = execution;
  useOnChange(executionEvents.length, () => reload({ silent: true }), REFRESH_DEBOUNCE_MS);

  if (!executed || (!execution.data && !execution.error)) return null;
  const data = execution.data;
  const operations = [...(data?.operations ?? [])].sort((a, b) => (a.week_number ?? 0) - (b.week_number ?? 0));
  const status = meta(EXECUTION_STATUS_META, data?.status);
  const summary = data?.summary;

  return (
    <Card title="Operasi Moodle" actions={data && <Badge tone={status.tone}>{status.label}</Badge>}>
      <ErrorAlert error={execution.error} />
      {data && (
        <>
          {summary?.total > 0 && (
            <p className="mb-3 text-sm text-muted">
              {summary.success} berhasil · {summary.failed} gagal · {summary.skipped} dilewati dari {summary.total} operasi
            </p>
          )}
          {data.error_message && <p className="mb-3 text-sm text-danger">{data.error_message}</p>}
          {operations.length ? (
            <div className="max-w-full overflow-x-auto" role="region" aria-label="Tabel operasi Moodle" tabIndex={0}>
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">Jenis operasi</th>
                    <th scope="col">Minggu</th>
                    <th scope="col">Status</th>
                    <th scope="col">Keterangan</th>
                  </tr>
                </thead>
                <tbody>
                  {operations.map((operation) => {
                    const opStatus = meta(OPERATION_STATUS_META, operation.status);
                    return (
                      <tr key={operation.operation_id}>
                        <td>{OPERATION_TYPE_LABELS[operation.operation_type] ?? operation.operation_type}</td>
                        <td>{operation.week_number ?? '-'}</td>
                        <td><Badge tone={opStatus.tone}>{opStatus.label}</Badge></td>
                        <td className="text-sm">{operation.error_message ?? (operation.retry_count > 0 ? `Dicoba ulang ${operation.retry_count} kali` : '')}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted">Belum ada operasi yang dijalankan.</p>
          )}
        </>
      )}
    </Card>
  );
}
