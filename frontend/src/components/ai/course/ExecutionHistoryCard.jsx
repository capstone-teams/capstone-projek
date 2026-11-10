import { Badge, Card } from '../../ui';
import { formatDateTime } from '../../../utils/format';

/**
 * Daftar riwayat eksekusi struktur Moodle pada workflow ini (FE-13.2).
 * Dosen dapat melihat eksekusi sebelumnya dan beralih untuk meninjau rinciannya.
 */
export default function ExecutionHistoryCard({
  executions = [],
  activeExecutionId,
  onSelectExecution,
}) {
  if (!executions || executions.length === 0) return null;

  return (
    <Card title="Riwayat Eksekusi Struktur Moodle">
      <p className="text-sm text-muted mb-4">
        Daftar seluruh proses eksekusi struktur course plan yang pernah dijalankan untuk alur kerja ini.
      </p>

      <div className="divide-y divide-line rounded-lg border border-line bg-surface">
        {executions.map((item) => {
          const isSelected = item.execution_id === activeExecutionId;
          const statusTone = item.status === 'SUCCESS'
            ? 'success'
            : item.status === 'FAILED'
            ? 'danger'
            : 'info';

          return (
            <div
              key={item.execution_id}
              className={`flex flex-wrap items-center justify-between gap-3 p-3.5 transition-colors ${
                isSelected ? 'bg-primary-light/10' : 'hover:bg-surface-subtle/50'
              }`}
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-ink">
                    {item.execution_id}
                  </span>
                  <Badge tone={statusTone}>{item.status}</Badge>
                  {isSelected && (
                    <span className="text-[11px] font-semibold text-primary uppercase tracking-wider">
                      ● Sedang Ditinjau
                    </span>
                  )}
                </div>
                <div className="text-xs text-muted mt-1 space-x-3">
                  <span>Dibuat: {formatDateTime(item.created_at)}</span>
                  <span>·</span>
                  <span>
                    Hasil: <strong>{item.summary?.success ?? 0}</strong>/{item.summary?.total ?? 16} Section Berhasil
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
