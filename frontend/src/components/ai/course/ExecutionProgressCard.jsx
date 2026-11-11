import { Link } from 'react-router-dom';
import { Alert, Badge, Card, ProgressBar, Spinner } from '../../ui';
import ExecutionOperationsTable from './ExecutionOperationsTable';
import ExecutionReadbackCard from './ExecutionReadbackCard';
import { EXECUTION_SCOPE } from '../../../services/executionService';
import { isFullScopeExecution } from '../../../utils/executionReadiness';
import { formatDateTime } from '../../../utils/format';

function describeReadbackFailure(readback) {
  if (!readback) return null;
  if (!readback.checked) {
    return readback.error ? `Gagal membaca ulang Moodle: ${readback.error}` : null;
  }
  if (readback.matches) return null;

  const issues = [];
  if (Array.isArray(readback.missing_weeks) && readback.missing_weeks.length > 0) {
    issues.push(`minggu belum ditemukan: Minggu ${readback.missing_weeks.join(', ')}`);
  }
  if (Array.isArray(readback.mismatched_weeks) && readback.mismatched_weeks.length > 0) {
    issues.push(`nama section berbeda pada Minggu ${readback.mismatched_weeks.join(', ')}`);
  }
  if (readback.ordered === false) {
    issues.push(
      `urutan section di Moodle belum rapi (terdeteksi ${readback.actual_sections ?? 0} dari ${readback.expected_sections ?? 16})`,
    );
  }
  if (issues.length === 0 && (readback.actual_sections ?? 0) !== (readback.expected_sections ?? 16)) {
    issues.push(`jumlah section ${readback.actual_sections ?? 0} dari ${readback.expected_sections ?? 16}`);
  }
  return issues.length > 0 ? issues.join('; ') : null;
}

function scrollToReadbackPanel() {
  const target = document.getElementById('execution-readback');
  target?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
}

/**
 * Kartu pemantauan progres dan detail eksekusi Moodle (FE-13.2 & FE-18.1).
 * Menampilkan progress bar, metrik operasi, detail per minggu/konten, read-back,
 * tombol ulangi operasi gagal (retry), serta tautan ke tab Kursus Moodle.
 */
export default function ExecutionProgressCard({
  execution,
  plan,
  courseUrl = null,
  verificationUrl = null,
  onRetry,
  retrying = false,
}) {
  if (!execution) return null;

  const isFull = isFullScopeExecution(execution);
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

  const successCount = summary.success ?? 0;
  const failedCount = summary.failed ?? 0;
  const skippedCount = summary.skipped ?? 0;
  const totalCount = summary.total ?? 16;
  const actionableTotal = isFull && skippedCount > 0
    ? Math.max(0, totalCount - skippedCount)
    : totalCount;
  const completedCount = actionableTotal === 0 && totalCount > 0 ? totalCount : successCount;
  const progressTotal = actionableTotal === 0 && totalCount > 0 ? totalCount : actionableTotal;
  const resolvedScope = isFull ? EXECUTION_SCOPE.FULL : (execution.scope || EXECUTION_SCOPE.STRUCTURE);
  const scopeDisplayLabel = resolvedScope === EXECUTION_SCOPE.FULL
    ? 'Lengkap — Struktur + Konten (FULL)'
    : 'Struktur Saja (STRUCTURE)';
  const readbackFailureDetail = describeReadbackFailure(execution.readback);
  const readbackOnlyFailure = isFailed && failedCount === 0 && Boolean(execution.readback && !execution.readback.matches);

  return (
    <Card
      title={isFull ? 'Status Eksekusi Course Moodle' : 'Status Eksekusi Struktur Moodle'}
      actions={(
        <div className="flex flex-wrap items-center gap-2">
          {courseUrl && (
            <Link to={courseUrl} className="btn btn--secondary btn--xs">
              Buka Tab Kursus →
            </Link>
          )}
          {isRunning && <Spinner size="sm" />}
          <Badge tone={statusTone}>{status}</Badge>
        </div>
      )}
    >
      <div className="space-y-5">
        {/* Informasi Identitas & Waktu Pelaksanaan */}
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted border-b border-line pb-3">
          <div>
            Eksekusi ID: <span className="font-mono font-semibold text-ink">{execution.execution_id}</span> · Mode: <span className="font-medium text-ink">{scopeDisplayLabel}</span>
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

        {/* Progress Bar Penyelesaian */}
        <div className="rounded-lg border border-line bg-surface p-4">
          <ProgressBar
            completed={completedCount}
            total={progressTotal}
            label={isFull ? 'Operasi Course Moodle Diterapkan' : 'Section Moodle Diterapkan'}
          />
          {isFull && skippedCount > 0 && (
            <p className="mt-1.5 text-xs text-muted">
              {skippedCount} dari {totalCount} operasi berstatus dilewati (jenis konten nonaktif atau belum memiliki versi disetujui).
            </p>
          )}
        </div>

        {/* Banner Status & Peringatan */}
        {isRunning ? (
          <Alert tone="info">
            <div className="flex items-center gap-2">
              <span>
                {isFull
                  ? 'Eksekusi section dan seluruh konten yang disetujui sedang dijalankan di background Moodle. Progres tiap operasi diperbarui otomatis di bawah.'
                  : 'Eksekusi struktur 16 minggu sedang dijadwalkan dan berjalan di background Moodle. Anda dapat memantau progres operasi tiap minggu di bawah.'}
              </span>
            </div>
          </Alert>
        ) : isSuccess ? (
          <Alert tone="success">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span>
                {isFull
                  ? 'Eksekusi section dan seluruh activity konten telah berhasil diterapkan ke kursus Moodle target. Lanjutkan ke Step 6 (Verifikasi) untuk menyelesaikan alur kerja.'
                  : 'Struktur 16 section mingguan telah berhasil dibuat pada kursus Moodle target.'}
              </span>
              <div className="flex flex-wrap items-center gap-3">
                {verificationUrl && (
                  <Link to={verificationUrl} relative="path" className="font-semibold underline">
                    Verifikasi Hasil di Moodle →
                  </Link>
                )}
                {courseUrl && (
                  <Link to={courseUrl} className="font-semibold underline">
                    Lihat hasil di Tab Kursus →
                  </Link>
                )}
              </div>
            </div>
          </Alert>
        ) : isFailed ? (
          <Alert
            tone="danger"
            title={readbackOnlyFailure
              ? 'Operasi Terkirim, Namun Struktur Moodle Belum Cocok'
              : 'Eksekusi Terhenti Sebagian'}
          >
            <div className="flex flex-wrap items-start justify-between gap-3 mt-1">
              <div className="space-y-1 text-sm min-w-0 flex-1">
                {readbackOnlyFailure ? (
                  <>
                    <p className="m-0">
                      Seluruh <strong>{successCount}</strong> operasi berhasil dikirim ke Moodle (<strong>Gagal: 0</strong>), tetapi pemeriksaan cepat struktur setelah eksekusi menemukan ketidaksesuaian
                      {readbackFailureDetail ? <>: <strong>{readbackFailureDetail}</strong>.</> : '.'}
                    </p>
                    <p className="m-0 text-xs">
                      {verificationUrl
                        ? 'Buka Step 6 (Verifikasi) untuk melihat teks Diharapkan vs Aktual di Moodle serta menjalankan perbaikan otomatis.'
                        : 'Periksa rincian ketidaksesuaian pada panel read-back di bawah untuk menyesuaikan struktur section Moodle.'}
                    </p>
                  </>
                ) : (
                  <span>
                    {execution.error_message || 'Sebagian atau seluruh operasi gagal diterapkan ke Moodle.'}
                    {readbackFailureDetail ? ` (${readbackFailureDetail})` : ''}
                  </span>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {verificationUrl && (
                  <Link
                    to={verificationUrl}
                    relative="path"
                    className={readbackOnlyFailure ? 'btn btn--primary btn--xs' : 'btn btn--secondary btn--xs'}
                  >
                    {readbackOnlyFailure ? 'Periksa & Perbaiki di Verifikasi →' : 'Verifikasi Hasil di Moodle →'}
                  </Link>
                )}
                {execution.readback && (
                  <button
                    type="button"
                    className="btn btn--secondary btn--xs"
                    onClick={scrollToReadbackPanel}
                  >
                    Lihat Rincian ↓
                  </button>
                )}
                {failedCount > 0 && onRetry && (
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

        {/* Panel Pemeriksaan Cepat Read-Back Struktur Moodle (Bila Tersedia) */}
        {execution.readback && (
          <ExecutionReadbackCard
            readback={execution.readback}
            verificationUrl={verificationUrl}
          />
        )}

        {/* Tabel Rincian Operasi */}
        <ExecutionOperationsTable
          operations={execution.operations || []}
          plan={plan}
          scope={resolvedScope}
        />
      </div>
    </Card>
  );
}
