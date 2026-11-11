import { Badge, Card } from '../../ui';
import { EXECUTION_SCOPE } from '../../../services/executionService';
import { formatDateTime } from '../../../utils/format';

/**
 * Daftar riwayat eksekusi Moodle pada workflow ini (FE-13.2 & FE-18.1).
 * Dosen dapat melihat eksekusi sebelumnya (STRUCTURE maupun FULL) dan meninjau rinciannya.
 */
export default function ExecutionHistoryCard({
  executions = [],
  activeExecutionId,
  onSelectExecution,
}) {
  if (!executions || executions.length === 0) return null;

  const hasFull = executions.some((item) => item?.scope === EXECUTION_SCOPE.FULL);

  return (
    <Card title={hasFull ? 'Riwayat Eksekusi Moodle' : 'Riwayat Eksekusi Struktur Moodle'}>
      <p className="text-sm text-muted mb-4">
        {hasFull
          ? 'Daftar seluruh proses eksekusi struktur dan konten yang pernah dijalankan untuk alur kerja ini.'
          : 'Daftar seluruh proses eksekusi struktur course plan yang pernah dijalankan untuk alur kerja ini.'}
      </p>

      <div className="divide-y divide-line rounded-lg border border-line bg-surface">
        {executions.map((item) => {
          const isSelected = item.execution_id === activeExecutionId;
          const isFull = item.scope === EXECUTION_SCOPE.FULL;
          const statusTone = item.status === 'SUCCESS'
            ? 'success'
            : item.status === 'FAILED'
            ? 'danger'
            : 'info';
          const skippedCount = item.summary?.skipped ?? 0;

          return (
            <div
              key={item.execution_id}
              className={`flex flex-wrap items-center justify-between gap-3 p-3.5 transition-colors ${
                isSelected ? 'bg-primary-light/10' : 'hover:bg-surface-subtle/50'
              }`}
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-ink">
                    {item.execution_id}
                  </span>
                  <Badge tone="neutral">{item.scope || EXECUTION_SCOPE.STRUCTURE}</Badge>
                  <Badge tone={statusTone}>{item.status}</Badge>
                  {isSelected && (
                    <span className="text-[11px] font-semibold text-primary uppercase tracking-wider">
                      ● Sedang Ditinjau
                    </span>
                  )}
                </div>
                <div className="text-xs text-muted mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5">
                  <span>Dibuat: {formatDateTime(item.created_at)}</span>
                  <span>·</span>
                  <span>
                    Hasil: <strong>{item.summary?.success ?? 0}</strong>/{item.summary?.total ?? 16}{' '}
                    {isFull ? 'Operasi Berhasil' : 'Section Berhasil'}
                    {skippedCount > 0 && ` (${skippedCount} dilewati)`}
                  </span>
                </div>
              </div>

              <div>
                {!isSelected && onSelectExecution && (
                  <button
                    type="button"
                    className="btn btn--secondary btn--xs"
                    onClick={() => onSelectExecution(item.execution_id)}
                  >
                    Tinjau Detail
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
