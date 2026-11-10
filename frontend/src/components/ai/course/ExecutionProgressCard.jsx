import { Alert, Badge, Card, ProgressBar, Spinner } from '../../ui';
import ExecutionOperationsTable from './ExecutionOperationsTable';
import ExecutionReadbackCard from './ExecutionReadbackCard';
import { formatDateTime } from '../../../utils/format';

/**
 * Kartu pemantauan progres dan detail eksekusi struktur Moodle (FE-13.2).
 * Menampilkan progress bar, metrik operasi, detail per minggu, hasil read-back,
 * dan tombol ulangi operasi gagal (retry).
 */
export default function ExecutionProgressCard({
  execution,
  plan,
  onRetry,
  retrying = false,
}) {
  if (!execution) return null;

  const summary = execution.summary || { total: 16, success: 0, failed: 0, skipped: 0 };
  const status = execution.status || 'PENDING';
  const isRunning = status === 'PENDING' || status === 'RUNNING';
  const isFailed = status === 'FAILED';
  const isSuccess = status === 'SUCCESS';

  const statusTone = isSuccess
    ? 'success'
    : isFailed
    ? 'danger'
    : 'info';

  const completedCount = summary.success ?? 0;
  const totalCount = summary.total ?? 16;

  return (
    <Card
      title="Status Eksekusi Struktur Moodle"
      actions={
        <div className="flex items-center gap-2">
          {isRunning && <Spinner size="sm" />}
          <Badge tone={statusTone}>{status}</Badge>
        </div>
      }
    >
      <div className="space-y-5">
        {/* Informasi Identitas & Waktu Pelaksanaan */}
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted border-b border-line pb-3">
          <div>
            Eksekusi ID: <span className="font-mono font-semibold text-ink">{execution.execution_id}</span> · Cakupan: <span className="font-mono text-ink">{execution.scope || 'STRUCTURE'}</span>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {execution.started_at && (
              <span>Mulai: <strong className="text-ink">{formatDateTime(execution.started_at)}</strong></span>
            )}
            {execution.completed_at && (
              <span>Selesai: <strong className="text-ink">{formatDateTime(execution.completed_at)}</strong></span>
            )}
          </div>
        </div>

        {/* Progress Bar Penyelesaian Section */}
        <div className="rounded-lg border border-line bg-surface p-4">
          <ProgressBar
            completed={completedCount}
            total={totalCount}
            label="Section Moodle Diterapkan"
          />
        </div>

        {/* Banner Status & Peringatan */}
        {isRunning ? (
          <Alert tone="info">
            <div className="flex items-center gap-2">
              <span>Eksekusi struktur 16 minggu sedang dijadwalkan dan berjalan di background Moodle. Anda dapat memantau progres operasi tiap minggu di bawah.</span>
            </div>
          </Alert>
        ) : isSuccess ? (
          <Alert tone="success">
            Struktur 16 section mingguan telah berhasil dibuat pada kursus Moodle target.
          </Alert>
        ) : isFailed ? (
          <Alert tone="danger" title="Eksekusi Terhenti Sebagian">
            <div className="flex flex-wrap items-center justify-between gap-3 mt-1">
              <span>
                {execution.error_message || 'Sebagian atau seluruh operasi struktur gagal diterapkan ke Moodle.'}
              </span>
              {summary.failed > 0 && onRetry && (
                <button
                  type="button"
                  className="btn btn--danger btn--xs"
                  disabled={retrying}
                  onClick={onRetry}
                >
                  {retrying ? 'Mengulang…' : 'Ulangi Operasi Gagal'}
                </button>
              )}
            </div>
          </Alert>
        ) : null}

        {/* Kartu Ringkasan 4 Metrik */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div className="rounded-lg border border-line bg-surface p-3">
            <div className="text-xs text-muted mb-1">Total Operasi</div>
            <div className="text-xl font-bold text-ink">{summary.total ?? 0}</div>
          </div>
          <div className="rounded-lg border border-line bg-surface p-3">
            <div className="text-xs text-muted mb-1">Berhasil</div>
            <div className="text-xl font-bold text-success">{summary.success ?? 0}</div>
          </div>
          <div className="rounded-lg border border-line bg-surface p-3">
            <div className="text-xs text-muted mb-1">Gagal</div>
            <div className="text-xl font-bold text-danger">{summary.failed ?? 0}</div>
          </div>
          <div className="rounded-lg border border-line bg-surface p-3">
            <div className="text-xs text-muted mb-1">Dilewati</div>
            <div className="text-xl font-bold text-muted">{summary.skipped ?? 0}</div>
          </div>
        </div>

        {/* Panel Verifikasi Read-Back Moodle (Bila Tersedia) */}
        {execution.readback && (
          <ExecutionReadbackCard readback={execution.readback} />
        )}

        {/* Tabel Rincian Operasi 16 Minggu */}
        <ExecutionOperationsTable
          operations={execution.operations || []}
          plan={plan}
        />
      </div>
    </Card>
  );
}
