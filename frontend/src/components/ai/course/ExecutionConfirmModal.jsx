import { Alert, Modal } from '../../ui';
import { CONTENT_KIND_LABELS } from '../../../services/contentService';
import { EXECUTION_SCOPE } from '../../../services/executionService';
import { CONTENT_KIND_ORDER } from '../../../utils/executionReadiness';

/**
 * Dialog konfirmasi sebelum memulai eksekusi course ke Moodle (FE-13.1, FE-18.1).
 * Menampilkan ringkasan target, jumlah section, jumlah activity (untuk FULL),
 * dan jaminan sifat idempotent.
 */
export default function ExecutionConfirmModal({
  open,
  onClose,
  onConfirm,
  courseTarget,
  weekCount = 16,
  scope = EXECUTION_SCOPE.STRUCTURE,
  activityCount = 0,
  activityCountsByKind = {},
  pending = false,
}) {
  const targetName = courseTarget?.fullname || courseTarget?.name || 'Mata Kuliah Target';
  const targetCode = courseTarget?.shortname || courseTarget?.code;
  const targetId = courseTarget?.moodle_course_id || courseTarget?.id;
  const isFull = scope === EXECUTION_SCOPE.FULL;

  const breakdownParts = CONTENT_KIND_ORDER
    .filter((kind) => (activityCountsByKind?.[kind] ?? 0) > 0)
    .map((kind) => `${activityCountsByKind[kind]} ${CONTENT_KIND_LABELS[kind]}`);

  return (
    <Modal
      open={open}
      title={isFull ? 'Konfirmasi Eksekusi Course ke Moodle' : 'Konfirmasi Eksekusi Struktur Course'}
      onClose={pending ? undefined : onClose}
      footer={
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            className="btn btn--ghost"
            disabled={pending}
            onClick={onClose}
          >
            Batal
          </button>
          <button
            type="button"
            className="btn btn--primary"
            disabled={pending}
            onClick={onConfirm}
          >
            {pending ? 'Memulai eksekusi…' : 'Ya, Mulai Eksekusi'}
          </button>
        </div>
      }
    >
      <div className="space-y-4">
        <p className="text-sm">
          {isFull ? (
            <>
              Sistem akan membuat atau memperbarui <strong>{weekCount} section mingguan</strong> beserta{' '}
              <strong>{activityCount} activity konten</strong> pada mata kuliah Moodle target berikut:
            </>
          ) : (
            <>
              Sistem akan membuat atau memperbarui struktur <strong>{weekCount} section mingguan</strong> pada mata kuliah Moodle target berikut:
            </>
          )}
        </p>

        <div className="rounded-lg border border-line bg-surface p-3.5 text-sm space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-muted">Mata Kuliah Moodle:</span>
            <span className="font-semibold text-ink text-right">{targetName}</span>
          </div>
          {targetCode && (
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted">Kode / Shortname:</span>
              <span className="font-mono text-xs">{targetCode}</span>
            </div>
          )}
          {targetId && (
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted">ID Kursus Moodle:</span>
              <span className="font-mono text-xs">#{targetId}</span>
            </div>
          )}
          <div className="flex items-center justify-between gap-2">
            <span className="text-muted">Jumlah Section:</span>
            <span className="font-semibold">{weekCount} Minggu (Minggu 1 s.d. {weekCount})</span>
          </div>
          {isFull && (
            <div className="flex items-start justify-between gap-2 pt-1 border-t border-line/60">
              <span className="text-muted">Jumlah Activity:</span>
              <div className="text-right">
                <span className="font-semibold block">{activityCount} Activity</span>
                {breakdownParts.length > 0 && (
                  <span className="text-xs text-muted">{breakdownParts.join(' · ')}</span>
                )}
              </div>
            </div>
          )}
        </div>

        <Alert tone="info">
          {isFull ? (
            <>
              Operasi ini bersifat <strong>idempotent</strong>. Section dan activity (Page, URL, Assignment, Quiz) yang sudah pernah dikirim akan diperbarui tanpa duplikasi.
            </>
          ) : (
            <>
              Operasi ini bersifat <strong>idempotent</strong>. Section yang nomornya sudah ada di Moodle akan disesuaikan judulnya tanpa menghapus modul aktivitas di dalamnya.
            </>
          )}
        </Alert>
      </div>
    </Modal>
  );
}
