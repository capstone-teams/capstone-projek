import { Link } from 'react-router-dom';
import {
  CONTENT_KIND_LABELS,
  CONTENT_STATUS,
  MAX_CONTENT_NOTE_LENGTH,
} from '../../../services/contentService';
import InstructionModal from '../InstructionModal';
import { Alert, Spinner } from '../../ui';

/** Tombol aksi regenerasi konten AI untuk diletakkan di header halaman aktivitas dosen. */
export function ActivityRegenerateButton({ state }) {
  if (!state?.supported) return null;
  return (
    <button
      type="button"
      className="btn btn--secondary btn--sm"
      disabled={!state.eligibility.allowed}
      title={state.eligibility.reason ?? 'Susun ulang isi aktivitas ini dengan AI'}
      onClick={state.openModal}
    >
      {state.busy ? 'Meregenerasi…' : 'Regenerasi konten'}
    </button>
  );
}

/** Banner progres & tautan tindak lanjut (Review -> Eksekusi FULL) untuk regenerasi konten aktivitas. */
export function ActivityRegenerateBanner({ courseId, state }) {
  if (!state?.supported) return null;
  const { workflow, operation, content, busy, startedNotice, clearNotice } = state;
  const aiBase = `/course/${courseId}/ai`;
  const hasNewerVersion = Boolean(content?.id && operation?.content_id && content.id !== operation.content_id);
  const readyToPublish = hasNewerVersion && content?.status === CONTENT_STATUS.APPROVED;
  const awaitingReview = hasNewerVersion && content?.status !== CONTENT_STATUS.APPROVED && content?.status !== CONTENT_STATUS.EXECUTED;

  if (busy) {
    return (
      <Alert tone="info" title="Regenerasi konten AI sedang berjalan">
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="inline-flex items-center gap-2">
            <Spinner size="sm" />
            <span>Agent sedang menyusun versi baru untuk aktivitas ini. Hasilnya akan masuk ke tab Review.</span>
          </span>
          <Link to={`${aiBase}/content`} className="font-semibold underline">
            Pantau di Tab Konten →
          </Link>
        </div>
      </Alert>
    );
  }

  if (readyToPublish) {
    return (
      <Alert tone="info" title={`Versi baru (v${content.version ?? '-'}) sudah disetujui`}>
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span>Jalankan ulang Eksekusi Moodle (FULL) agar perubahan diterapkan ke aktivitas Moodle ini.</span>
          <div className="flex flex-wrap items-center gap-3">
            <Link to={`${aiBase}/publish`} className="font-semibold underline">
              Buka Eksekusi Moodle →
            </Link>
            <Link to={`${aiBase}/review`} className="font-semibold underline">
              Lihat Review
            </Link>
          </div>
        </div>
      </Alert>
    );
  }

  if (awaitingReview) {
    return (
      <Alert tone="info" title={`Draf versi baru (v${content.version ?? '-'}) siap direview`}>
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span>
            Setujui versi baru di tab Review lalu terapkan ke Moodle untuk memperbarui isi aktivitas ini.
          </span>
          <Link to={`${aiBase}/review`} className="font-semibold underline">
            Buka Tab Review →
          </Link>
        </div>
      </Alert>
    );
  }

  if (startedNotice) {
    const failed = workflow?.status === 'FAILED';
    return (
      <Alert
        tone={failed ? 'danger' : 'info'}
        title={failed ? 'Regenerasi konten gagal' : 'Regenerasi konten dijadwalkan'}
        onClose={clearNotice}
      >
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span>{startedNotice}</span>
          <Link to={`${aiBase}/review`} className="font-semibold underline">
            Buka Tab Review →
          </Link>
        </div>
      </Alert>
    );
  }

  return null;
}

/** Dialog input catatan revisi wajib untuk memicu regenerasi konten aktivitas AI. */
export function ActivityRegenerateModal({ state }) {
  if (!state?.supported) return null;
  const kindLabel = CONTENT_KIND_LABELS[state.content?.kind] ?? 'Konten';
  const weekText = state.content?.week_number != null ? `Minggu ${state.content.week_number} — ` : '';

  return (
    <InstructionModal
      key={state.content?.id ?? 'closed'}
      open={state.modalOpen}
      title={`Regenerasi ${weekText}${kindLabel}`}
      label="Catatan revisi"
      hint="Wajib diisi. Hasil versi baru masuk ke tab Review untuk disetujui sebelum diterapkan ke Moodle."
      placeholder="Contoh: Sederhanakan penjelasan dan tambahkan contoh kode yang mudah diikuti."
      submitLabel="Mulai Regenerasi"
      maxLength={MAX_CONTENT_NOTE_LENGTH}
      onClose={state.closeModal}
      onSubmit={state.submitRegenerate}
    />
  );
}
