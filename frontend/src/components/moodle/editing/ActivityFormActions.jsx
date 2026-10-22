/**
 * Tombol bawah formulir pembuatan aktivitas. Bila aplikasi belum dapat membuat aktivitas
 * (Moodle nyata tanpa API pembuatan), tombol simpan diganti tautan ke formulir Moodle.
 */
export default function ActivityFormActions({ canCreate, moodleHref, pending, submitLabel, onBack }) {
  return (
    <div className="form__actions">
      <button type="button" className="btn btn--ghost" onClick={onBack}>
        ← Pilih jenis lain
      </button>
      {canCreate ? (
        <button type="submit" className="btn btn--primary" disabled={pending}>
          {pending ? 'Menyimpan…' : submitLabel}
        </button>
      ) : (
        <a href={moodleHref} target="_blank" rel="noreferrer" className="btn btn--primary">
          Lanjutkan di Moodle ↗<span className="sr-only"> (tab baru)</span>
        </a>
      )}
    </div>
  );
}
