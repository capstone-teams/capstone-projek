import { api } from './apiClient';

// Konten mingguan per workflow (BE-19.2 review, BE-19.3 generate/regenerate, /api/v1/workflows/{workflow_id}/contents).
// Aturan backend:
// - approve hanya untuk versi terbaru yang lolos validasi (status validasi PASSED) dan belum ditolak/dieksekusi;
//   satu konten yang tidak memenuhi syarat membuat seluruh permintaan ditolak 409, jadi pilihan dikirim sebagai
//   content_ids;
// - reject dan regenerate wajib membawa catatan revisi;
// - generate hanya setelah course plan terbaru APPROVED; jenis konten mengikuti Activity Configuration rencana.

/** Jenis konten (ContentKind backend). */
export const CONTENT_KIND = {
  LEARNING_MATERIAL: 'LEARNING_MATERIAL',
  RESOURCE: 'RESOURCE',
  ASSIGNMENT: 'ASSIGNMENT',
  QUIZ: 'QUIZ',
};

export const CONTENT_KIND_LABELS = {
  [CONTENT_KIND.LEARNING_MATERIAL]: 'Materi pembelajaran',
  [CONTENT_KIND.RESOURCE]: 'Sumber belajar',
  [CONTENT_KIND.ASSIGNMENT]: 'Tugas',
  [CONTENT_KIND.QUIZ]: 'Kuis',
};

/** Status approval satu versi konten (ApprovalStatus backend). */
export const CONTENT_STATUS = {
  DRAFT: 'DRAFT',
  VALIDATED: 'VALIDATED',
  PENDING_REVIEW: 'PENDING_REVIEW',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
  EXECUTED: 'EXECUTED',
};

export const CONTENT_STATUS_META = {
  [CONTENT_STATUS.DRAFT]: { label: 'Draft', tone: 'neutral' },
  [CONTENT_STATUS.VALIDATED]: { label: 'Tervalidasi', tone: 'info' },
  [CONTENT_STATUS.PENDING_REVIEW]: { label: 'Menunggu review', tone: 'warning' },
  [CONTENT_STATUS.APPROVED]: { label: 'Disetujui', tone: 'success' },
  [CONTENT_STATUS.REJECTED]: { label: 'Ditolak', tone: 'danger' },
  [CONTENT_STATUS.EXECUTED]: { label: 'Terkirim ke Moodle', tone: 'success' },
};

/** Status hasil validasi (ValidationStatus backend). */
export const VALIDATION_STATUS_META = {
  PASSED: { label: 'Lolos validasi', tone: 'success' },
  PARTIAL: { label: 'Lolos sebagian', tone: 'warning' },
  FAILED: { label: 'Tidak lolos validasi', tone: 'danger' },
};

/** Cakupan regenerasi (RegenerationScope backend). */
export const REGENERATION_SCOPE = { COURSE: 'COURSE', MINGGU: 'MINGGU', ITEM: 'ITEM' };

/** Batas catatan revisi, sama dengan catatan course plan. */
export const MAX_CONTENT_NOTE_LENGTH = 2000;

/** GET /workflows/{id}/contents: versi terbaru tiap konten, urut minggu; filter opsional. */
export function listWorkflowContents(workflowId, { weekNumber, kind, status } = {}) {
  const query = {};
  if (weekNumber != null) query.week_number = weekNumber;
  if (kind) query.content_type = kind;
  if (status) query.status = status;
  return api.get(`/workflows/${workflowId}/contents`, { query }).then((data) => data?.items ?? []);
}

/** GET /workflows/{id}/contents/{content_id}: detail satu versi (isi, validasi lengkap). */
export function getWorkflowContent(workflowId, contentId) {
  return api.get(`/workflows/${workflowId}/contents/${contentId}`);
}

/** GET /workflows/{id}/contents/{content_id}/versions: riwayat versi. */
export function listContentVersions(workflowId, contentId) {
  return api.get(`/workflows/${workflowId}/contents/${contentId}/versions`).then((data) => data?.items ?? []);
}

/** POST /workflows/{id}/contents/approve dengan content_ids terpilih. */
export function approveContents(workflowId, contentIds) {
  return api.post(`/workflows/${workflowId}/contents/approve`, { content_ids: contentIds });
}

/** POST /workflows/{id}/contents/reject dengan content_ids terpilih dan catatan revisi wajib. */
export function rejectContents(workflowId, contentIds, notes) {
  return api.post(`/workflows/${workflowId}/contents/reject`, { content_ids: contentIds, notes });
}

/** POST /workflows/{id}/contents/generate untuk seluruh minggu (202, dikerjakan di belakang). */
export function generateContents(workflowId) {
  return api.post(`/workflows/${workflowId}/contents/generate`, { weeks: 'all' });
}

/**
 * POST /workflows/{id}/contents/regenerate. COURSE: seluruh konten; MINGGU: weekNumber wajib; ITEM: contentId wajib.
 */
export function regenerateContents(workflowId, { scope, weekNumber, contentId, notes }) {
  const body = { scope, notes };
  if (scope === REGENERATION_SCOPE.MINGGU) body.week_number = weekNumber;
  if (scope === REGENERATION_SCOPE.ITEM) body.content_id = contentId;
  return api.post(`/workflows/${workflowId}/contents/regenerate`, body);
}
