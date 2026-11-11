const COURSE_STATUS_LABELS = {
  CREATED: 'Baru dibuat',
  DRAFT: 'Draft',
  PLANNING: 'Menyusun rencana',
  WAITING_PLAN_REVIEW: 'Menunggu review rencana',
  PLAN_APPROVED: 'Rencana disetujui',
  GENERATING_CONTENT: 'Membuat konten',
  VALIDATING: 'Validasi konten',
  WAITING_CONTENT_REVIEW: 'Menunggu review konten',
  CONTENT_REJECTED: 'Konten perlu revisi',
  APPROVED: 'Siap dieksekusi',
  EXECUTING: 'Mengirim ke Moodle',
  EXECUTED: 'Terkirim ke Moodle',
  VERIFYING: 'Memverifikasi Moodle',
  COMPLETED: 'Selesai',
  FAILED: 'Gagal',
};

const COURSE_STATUS_TONES = {
  PLANNING: 'info',
  GENERATING_CONTENT: 'info',
  VALIDATING: 'info',
  EXECUTING: 'info',
  VERIFYING: 'info',
  WAITING_PLAN_REVIEW: 'warning',
  WAITING_CONTENT_REVIEW: 'warning',
  CONTENT_REJECTED: 'warning',
  PLAN_APPROVED: 'success',
  APPROVED: 'success',
  EXECUTED: 'success',
  COMPLETED: 'success',
  FAILED: 'danger',
};

const BADGE_TONES = {
  neutral: 'bg-surface text-ink border border-line',
  success: 'bg-success-light text-success',
  warning: 'bg-warning-light text-warning',
  danger: 'bg-danger-light text-danger',
  info: 'bg-primary-light text-primary',
  primary: 'bg-primary text-white',
};

export function Badge({ tone = 'neutral', children }) {
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded px-2 py-0.5 text-xs font-bold ${BADGE_TONES[tone] ?? BADGE_TONES.neutral}`}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }) {
  return <Badge tone={COURSE_STATUS_TONES[status] ?? 'neutral'}>{COURSE_STATUS_LABELS[status] ?? status}</Badge>;
}
