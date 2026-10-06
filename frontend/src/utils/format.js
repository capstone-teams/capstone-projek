const dateTimeFormat = new Intl.DateTimeFormat('id-ID', { dateStyle: 'medium', timeStyle: 'short' });
const timeFormat = new Intl.DateTimeFormat('id-ID', { timeStyle: 'medium' });

export function formatDateTime(value) {
  if (!value) return '-';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : dateTimeFormat.format(d);
}

export function formatTime(value) {
  if (!value) return '-';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : timeFormat.format(d);
}

export function formatFileSize(bytes) {
  if (bytes == null) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function percent(completed, total) {
  if (!total) return 0;
  return Math.round((completed / total) * 100);
}

export function errorMessage(error) {
  if (!error) return '';
  return error.message || 'Terjadi kesalahan.';
}

// ---- Timestamp Moodle (detik sejak epoch)
const dayFormat = new Intl.DateTimeFormat('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
const shortFormat = new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
const clockFormat = new Intl.DateTimeFormat('id-ID', { hour: '2-digit', minute: '2-digit' });

export function fromUnix(ts) {
  return ts ? new Date(ts * 1000) : null;
}

export function formatUnixDay(ts) {
  return ts ? dayFormat.format(fromUnix(ts)) : '-';
}

export function formatUnixDateTime(ts) {
  return ts ? `${shortFormat.format(fromUnix(ts))}, ${clockFormat.format(fromUnix(ts))}` : '-';
}

export function formatUnixTime(ts) {
  return ts ? clockFormat.format(fromUnix(ts)) : '-';
}

/** "3 hari lalu" / "Belum pernah" untuk last access. */
export function formatRelative(ts) {
  if (!ts) return 'Belum pernah';
  const diff = Math.round(Date.now() / 1000 - ts);
  if (diff < 60) return 'Baru saja';
  if (diff < 3600) return `${Math.floor(diff / 60)} menit lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} jam lalu`;
  return `${Math.floor(diff / 86400)} hari lalu`;
}

/** Ambil cmid dari URL Moodle seperti .../mod/assign/view.php?id=42 */
export function cmidFromUrl(url) {
  const m = /[?&]id=(\d+)/.exec(url ?? '');
  return m ? Number(m[1]) : null;
}
