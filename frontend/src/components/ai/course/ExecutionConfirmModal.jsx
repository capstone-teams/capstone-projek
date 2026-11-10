import { Alert, Modal } from '../../ui';

/**
 * Dialog konfirmasi sebelum memulai eksekusi struktur course ke Moodle (FE-13.1).
 * Menampilkan ringkasan target, jumlah section, dan jaminan sifat idempotent.
 */
export default function ExecutionConfirmModal({
  open,
  onClose,
  onConfirm,
  courseTarget,
  weekCount = 16,
  pending = false,
}) {
  const targetName = courseTarget?.fullname || courseTarget?.name || 'Mata Kuliah Target';
  const targetCode = courseTarget?.shortname || courseTarget?.code;
  const targetId = courseTarget?.moodle_course_id || courseTarget?.id;

  return (
    <Modal
      open={open}
      title="Konfirmasi Eksekusi Struktur Course"
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
          Sistem akan membuat atau memperbarui struktur <strong>{weekCount} section mingguan</strong> pada mata kuliah Moodle target berikut:
        </p>

        <div className="rounded-lg border border-line bg-surface p-3.5 text-sm space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-muted">Mata Kuliah Moodle:</span>
            <span className="font-semibold text-ink">{targetName}</span>
          </div>
          {targetCode && (
            <div className="flex items-center justify-between">
              <span className="text-muted">Kode / Shortname:</span>
              <span className="font-mono text-xs">{targetCode}</span>
            </div>
          )}
          {targetId && (
            <div className="flex items-center justify-between">
              <span className="text-muted">ID Kursus Moodle:</span>
              <span className="font-mono text-xs">#{targetId}</span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-muted">Jumlah Minggu:</span>
            <span className="font-semibold">{weekCount} Minggu (Minggu 1 s.d. {weekCount})</span>
          </div>
        </div>

        <Alert tone="info">
          Operasi ini bersifat <strong>idempotent</strong>. Section yang nomornya sudah ada di Moodle akan disesuaikan judulnya tanpa menghapus modul aktivitas di dalamnya.
        </Alert>
      </div>
    </Modal>
  );
}
