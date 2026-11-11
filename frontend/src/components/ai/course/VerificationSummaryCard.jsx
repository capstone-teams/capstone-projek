import { Link } from 'react-router-dom';
import { Alert, Badge, Card, Spinner } from '../../ui';
import {
  VERIFICATION_STATUS,
  VERIFICATION_STATUS_META,
} from '../../../services/verificationService';
import { isVerificationPassed } from '../../../utils/verificationResult';
import { formatDateTime } from '../../../utils/format';

function StatusBanner({ verification, courseUrl, publishUrl }) {
  const status = verification.status;
  const repairCount = verification.repair_count ?? 0;
  const repairRounds = verification.repair_rounds ?? 0;
  const remainingCount = verification.discrepancies?.length ?? 0;

  if (status === VERIFICATION_STATUS.PASS || verification.matches === true) {
    return (
      <Alert tone="success" title="Course sesuai rencana (COMPLETED)">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span>
            Seluruh section mingguan dan aktivitas konten di Moodle telah sesuai dengan course plan serta konten yang disetujui.
            {repairCount > 0 && ` Sebanyak ${repairCount} ketidaksesuaian berhasil diperbaiki otomatis (${repairRounds} putaran).`}
          </span>
          {courseUrl && (
            <Link to={courseUrl} className="font-semibold underline">
              Lihat hasil di Tab Kursus →
            </Link>
          )}
        </div>
      </Alert>
    );
  }

  if (status === VERIFICATION_STATUS.PARTIAL) {
    return (
      <Alert tone="warning" title="Sesuai dengan catatan tambahan di Moodle">
        <p className="m-0">
          Seluruh section dan konten hasil eksekusi sudah tersedia di Moodle, tetapi ditemukan{' '}
          <strong>{remainingCount} aktivitas tambahan</strong> yang ditambahkan langsung di Moodle dan sengaja tidak dihapus sistem.
          {repairCount > 0 && ` (${repairCount} perbedaan lain diperbaiki otomatis dalam ${repairRounds} putaran.)`}
        </p>
      </Alert>
    );
  }

  if (status === VERIFICATION_STATUS.UNKNOWN) {
    return (
      <Alert tone="danger" title="Moodle tidak dapat dibaca saat verifikasi">
        <p className="m-0">
          {verification.error_message || 'Koneksi ke server Moodle gagal saat membaca isi course.'}
        </p>
      </Alert>
    );
  }

  return (
    <Alert tone="danger" title="Masih terdapat perbedaan setelah perbaikan otomatis">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span>
          Tersisa <strong>{remainingCount} ketidaksesuaian</strong> setelah {repairRounds} putaran perbaikan otomatis
          {repairCount > 0 ? ` (${repairCount} item diperbaiki)` : ''}. Periksa rincian per minggu di bawah lalu coba{' '}
          <strong>Verifikasi Ulang</strong> atau tinjau eksekusi di halaman Eksekusi Moodle.
        </span>
        {publishUrl && (
          <Link to={publishUrl} relative="path" className="font-semibold underline">
            Buka Eksekusi Moodle →
          </Link>
        )}
      </div>
    </Alert>
  );
}

/**
 * Kartu ringkasan hasil verifikasi Moodle terbaru atau yang sedang ditinjau (FE-18.2).
 */
export default function VerificationSummaryCard({
  verification,
  workflowCompleted = false,
  canVerify = false,
  runningExecution = false,
  verifying = false,
  viewingOlder = false,
  courseUrl = null,
  publishUrl = '../publish',
  onVerify,
  onBackToLatest,
}) {
  if (!verification) return null;

  const meta = VERIFICATION_STATUS_META[verification.status] ?? {
    label: verification.status || 'Tidak diketahui',
    tone: 'neutral',
  };
  const passed = isVerificationPassed(verification);
  const isCompleted = workflowCompleted || passed;
  const summary = verification.summary || {};
  const remainingCount = verification.discrepancies?.length ?? 0;
  const repairCount = verification.repair_count ?? 0;
  const repairRounds = verification.repair_rounds ?? 0;
  const expectedSections = summary.expected_sections ?? 0;
  const actualSections = summary.actual_sections ?? 0;
  const expectedActivities = summary.expected_activities ?? 0;
  const foundActivities = summary.found_activities ?? 0;

  return (
    <Card
      title="Hasil Verifikasi Moodle"
      actions={(
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={meta.tone}>{meta.label}</Badge>
          {isCompleted && <Badge tone="success">COMPLETED</Badge>}
          {courseUrl && (
            <Link to={courseUrl} className="btn btn--secondary btn--xs">
              Buka Tab Kursus →
            </Link>
          )}
          {onVerify && (
            <button
              type="button"
              className="btn btn--primary btn--xs"
              disabled={!canVerify || verifying || runningExecution}
              onClick={onVerify}
            >
              {verifying ? (
                <span className="inline-flex items-center gap-1.5">
                  <Spinner size="sm" />
                  <span>Memverifikasi…</span>
                </span>
              ) : (
                'Verifikasi Ulang'
              )}
            </button>
          )}
        </div>
      )}
    >
      <div className="space-y-4">
        {viewingOlder && (
          <Alert tone="info" title="Menampilkan riwayat verifikasi terdahulu">
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span>Anda sedang meninjau hasil verifikasi lama, bukan pemeriksaan terbaru.</span>
              {onBackToLatest && (
                <button type="button" className="font-semibold underline" onClick={onBackToLatest}>
                  Kembali ke hasil terbaru
                </button>
              )}
            </div>
          </Alert>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3 text-xs text-muted">
          <div>
            Verifikasi ID: <span className="font-mono font-semibold text-ink">{verification.verification_id}</span>
            {verification.execution_id && (
              <>
                {' '}· Eksekusi: <span className="font-mono text-ink">{verification.execution_id}</span>
              </>
            )}
          </div>
          <div>
            Waktu verifikasi: <strong className="text-ink">{formatDateTime(verification.verified_at)}</strong>
          </div>
        </div>

        <StatusBanner verification={verification} courseUrl={courseUrl} publishUrl={publishUrl} />

        <div className="grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
          <div className="rounded-lg border border-line bg-surface p-3">
            <div className="mb-1 text-xs text-muted">Section Sesuai</div>
            <div className="text-xl font-bold text-ink">
              {actualSections} / {expectedSections}
            </div>
          </div>
          <div className="rounded-lg border border-line bg-surface p-3">
            <div className="mb-1 text-xs text-muted">Activity Sesuai</div>
            <div className="text-xl font-bold text-ink">
              {foundActivities} / {expectedActivities}
            </div>
          </div>
          <div className="rounded-lg border border-line bg-surface p-3">
            <div className="mb-1 text-xs text-muted">Perbaikan Otomatis</div>
            <div className={`text-xl font-bold ${repairCount > 0 ? 'text-success' : 'text-ink'}`}>
              {repairCount}
            </div>
            <div className="text-[11px] text-muted">{repairRounds} putaran</div>
          </div>
          <div className="rounded-lg border border-line bg-surface p-3">
            <div className="mb-1 text-xs text-muted">Sisa Perbedaan</div>
            <div className={`text-xl font-bold ${remainingCount > 0 ? 'text-danger' : 'text-success'}`}>
              {remainingCount}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
