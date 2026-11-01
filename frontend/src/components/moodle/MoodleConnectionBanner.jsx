import { Alert, Badge } from '../ui';

/**
 * Banner status koneksi ke Moodle LMS (FE-09.1).
 * Menampilkan indikator status koneksi backend ke instance Moodle dan penanganan gracefully
 * jika Moodle tidak dapat dijangkau tanpa merusak tampilan halaman.
 */
export default function MoodleConnectionBanner({
  status,
  moodleUrl,
  message,
  loading = false,
  error = null,
  onRetry,
}) {
  if (loading && !status && !error) {
    return (
      <div className="mb-4 rounded-lg border border-line bg-surface p-3 text-sm text-muted" role="status">
        <span className="inline-block animate-pulse">Memeriksa koneksi Moodle LMS…</span>
      </div>
    );
  }

  const isConnected = status === 'CONNECTED' && !error;

  if (isConnected) {
    return (
      <div
        className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50/80 px-4 py-3 text-sm text-emerald-900"
        aria-label="Status koneksi Moodle"
      >
        <div className="flex items-center gap-2">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-600" aria-hidden="true" />
          <span className="font-semibold">Moodle LMS Terhubung</span>
          {moodleUrl && (
            <span className="text-emerald-700">({moodleUrl})</span>
          )}
        </div>
        {message && <span className="text-xs text-emerald-700">{message}</span>}
      </div>
    );
  }

  // DISCONNECTED atau terjadi Error
  return (
    <div
      className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-start gap-2.5">
        <span className="mt-1 inline-block h-2.5 w-2.5 shrink-0 rounded-full bg-amber-500" aria-hidden="true" />
        <div>
          <p className="font-semibold">Koneksi ke Moodle LMS Terputus</p>
          <p className="text-xs text-amber-800">
            {error?.message || message || 'Instance Moodle LMS ITK tidak dapat dijangkau. Pastikan server Moodle aktif.'}
          </p>
        </div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          disabled={loading}
          className="btn btn--secondary text-xs"
        >
          {loading ? 'Memeriksa…' : 'Coba Lagi'}
        </button>
      )}
    </div>
  );
}
