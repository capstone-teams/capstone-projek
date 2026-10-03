// Status workflow course (design-api.md §20).
// PLAN_APPROVED, CONTENT_REJECTED, dan EXECUTED adalah status antara yang diasumsikan
// frontend; sesuaikan bila backend memakai nama lain.

export const STATUS_LABELS = {
  CREATED: 'Dibuat',
  PROCESSING_RPS: 'Memproses RPS',
  ANALYZING_RPS: 'Menganalisis RPS',
  PLANNING: 'Menyusun rencana',
  WAITING_PLAN_REVIEW: 'Menunggu review rencana',
  PLAN_APPROVED: 'Rencana disetujui',
  GENERATING_CONTENT: 'Membuat konten',
  VALIDATING: 'Validasi konten',
  WAITING_CONTENT_REVIEW: 'Menunggu review konten',
  CONTENT_REJECTED: 'Konten perlu revisi',
  APPROVED: 'Konten disetujui',
  EXECUTING: 'Mengirim ke Moodle',
  EXECUTED: 'Terkirim ke Moodle',
  VERIFYING: 'Verifikasi Moodle',
  COMPLETED: 'Selesai',
  FAILED: 'Gagal',
};

const BUSY = ['PROCESSING_RPS', 'ANALYZING_RPS', 'PLANNING', 'GENERATING_CONTENT', 'VALIDATING', 'EXECUTING', 'VERIFYING'];
const ACTION = ['WAITING_PLAN_REVIEW', 'WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED', 'EXECUTED'];

export function statusTone(status) {
  if (status === 'COMPLETED') return 'success';
  if (status === 'FAILED') return 'danger';
  if (BUSY.includes(status)) return 'info';
  if (ACTION.includes(status)) return 'warning';
  return 'neutral';
}

export function isBusy(status) {
  return BUSY.includes(status);
}

export const WORKFLOW_STEPS = [
  { key: 'plan', label: 'Rencana', statuses: ['CREATED', 'PLANNING', 'WAITING_PLAN_REVIEW'] },
  { key: 'content', label: 'Konten', statuses: ['PLAN_APPROVED', 'GENERATING_CONTENT', 'VALIDATING'] },
  { key: 'review', label: 'Review', statuses: ['WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED'] },
  { key: 'execution', label: 'Eksekusi Moodle', statuses: ['APPROVED', 'EXECUTING'] },
  { key: 'verification', label: 'Verifikasi', statuses: ['EXECUTED', 'VERIFYING'] },
  { key: 'done', label: 'Selesai', statuses: ['COMPLETED'] },
];

export function currentStepIndex(status) {
  const i = WORKFLOW_STEPS.findIndex((s) => s.statuses.includes(status));
  return i === -1 ? 0 : i;
}

export const RPS_STATUS_LABELS = {
  uploaded: 'Diunggah',
  processing: 'Diproses',
  analyzing: 'Dianalisis',
  processed: 'Siap',
  failed: 'Gagal',
};

export const RUN_TYPE_LABELS = {
  rps_processing: 'Pemrosesan RPS',
  course_planning: 'Perencanaan course',
  content_generation: 'Generate konten',
  content_regeneration: 'Regenerasi konten',
  validation: 'Validasi',
  moodle_execution: 'Eksekusi Moodle',
  verification: 'Verifikasi',
};

export const EVENT_LABELS = {
  COURSE_CREATED: 'Course dibuat',
  STATUS_CHANGED: 'Status berubah',
  PLANNING_STARTED: 'Penyusunan rencana dimulai',
  PLANNING_PROGRESS: 'Menyusun rencana mingguan',
  PLANNING_COMPLETED: 'Rencana selesai disusun',
  PLAN_APPROVED: 'Rencana disetujui',
  CONTENT_GENERATION_STARTED: 'Generate konten dimulai',
  CONTENT_GENERATION_COMPLETED: 'Generate konten selesai',
  VALIDATION_STARTED: 'Validasi dimulai',
  VALIDATION_COMPLETED: 'Validasi selesai',
  CONTENT_APPROVED: 'Konten disetujui',
  CONTENT_REJECTED: 'Konten ditolak',
  EXECUTION_STARTED: 'Eksekusi ke Moodle dimulai',
  EXECUTION_PROGRESS: 'Eksekusi berjalan',
  EXECUTION_COMPLETED: 'Eksekusi selesai',
  EXECUTION_CANCELLED: 'Eksekusi dibatalkan',
  VERIFICATION_STARTED: 'Verifikasi dimulai',
  VERIFICATION_CHECK: 'Pemeriksaan verifikasi',
  VERIFICATION_COMPLETED: 'Verifikasi selesai',
};

export function describeEvent(ev) {
  const label = EVENT_LABELS[ev.event] ?? ev.event;
  if (ev.event === 'STATUS_CHANGED') return `${label}: ${STATUS_LABELS[ev.status] ?? ev.status}`;
  if (ev.week) return `${label} — minggu ${ev.week}`;
  if (ev.result) return `${label} (${ev.result})`;
  if (ev.reason) return `${label}: ${ev.reason}`;
  return label;
}
