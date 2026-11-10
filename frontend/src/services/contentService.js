import { api } from './apiClient';

// Konten mingguan berbasis workflow (BE-19.2 review, BE-19.3 generate/regenerate, /api/v1/workflows/{workflow_id}/contents).
// Aturan backend:
// - approve hanya untuk versi terbaru yang lolos validasi (status validasi PASSED) dan belum ditolak/dieksekusi;
//   satu konten yang tidak memenuhi syarat membuat seluruh permintaan ditolak 409, jadi pilihan dikirim sebagai
//   content_ids;
// - reject dan regenerate wajib membawa catatan revisi;
// - generate hanya setelah course plan terbaru APPROVED; jenis konten mengikuti Activity Configuration rencana.

/** Jenis konten hasil generation (backend src/services/content/domain.py: ContentKind). */
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

/** Alias kompatibilitas untuk modul FE-16 yang mengimpor APPROVAL_STATUS. */
export const APPROVAL_STATUS = CONTENT_STATUS;

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

/** Cakupan regenerasi konten (RegenerationScope backend). */
export const REGENERATION_SCOPE = {
  COURSE: 'COURSE',
  MINGGU: 'MINGGU',
  ITEM: 'ITEM',
};

/** Batas catatan revisi, sama dengan catatan course plan. */
export const MAX_CONTENT_NOTE_LENGTH = 2000;

/**
 * GET /api/v1/workflows/{workflow_id}/contents
 * Versi terbaru tiap konten pada workflow, urut minggu; filter opsional.
 */
export function listWorkflowContents(
  workflowId,
  { weekNumber, week_number, kind, content_type, status } = {},
) {
  const query = {};
  const targetWeek = weekNumber ?? week_number;
  const targetKind = kind ?? content_type;
  if (targetWeek != null) query.week_number = targetWeek;
  if (targetKind) query.content_type = targetKind;
  if (status) query.status = status;
  return api.get(`/workflows/${workflowId}/contents`, { query }).then((data) => data?.items ?? []);
}

/** GET /api/v1/workflows/{workflow_id}/contents/{content_id}: detail satu versi (isi, validasi lengkap). */
export function getWorkflowContent(workflowId, contentId) {
  return api.get(`/workflows/${workflowId}/contents/${contentId}`);
}

/** GET /api/v1/workflows/{workflow_id}/contents/{content_id}/versions: riwayat versi. */
export function listContentVersions(workflowId, contentId) {
  return api.get(`/workflows/${workflowId}/contents/${contentId}/versions`).then((data) => data?.items ?? []);
}

/** POST /api/v1/workflows/{workflow_id}/contents/approve dengan content_ids terpilih. */
export function approveContents(workflowId, contentIds) {
  return api.post(`/workflows/${workflowId}/contents/approve`, { content_ids: contentIds });
}

/** POST /api/v1/workflows/{workflow_id}/contents/reject dengan content_ids terpilih dan catatan revisi wajib. */
export function rejectContents(workflowId, contentIds, notes) {
  return api.post(`/workflows/${workflowId}/contents/reject`, { content_ids: contentIds, notes });
}

/**
 * POST /api/v1/workflows/{workflow_id}/contents/generate
 * Memulai generation konten untuk seluruh minggu ('all') atau daftar nomor minggu ([1, 2, ...]).
 */
export function generateWorkflowContents(workflowId, weeks = 'all') {
  return api.post(`/workflows/${workflowId}/contents/generate`, { weeks });
}

/** Alias kompatibilitas untuk pemanggil FE-17 (`generateContents(workflowId)`). */
export const generateContents = generateWorkflowContents;

/**
 * POST /api/v1/workflows/{workflow_id}/contents/regenerate
 * COURSE: seluruh konten; MINGGU: weekNumber/week_number wajib; ITEM: contentId/content_id wajib.
 */
export function regenerateContents(
  workflowId,
  { scope = REGENERATION_SCOPE.ITEM, weekNumber, week_number, contentId, content_id, notes },
) {
  const body = { scope, notes };
  const targetWeek = weekNumber ?? week_number;
  const targetContent = contentId ?? content_id;
  if (scope === REGENERATION_SCOPE.MINGGU) body.week_number = targetWeek;
  if (scope === REGENERATION_SCOPE.ITEM) body.content_id = targetContent;
  return api.post(`/workflows/${workflowId}/contents/regenerate`, body);
}

/** Alias kompatibilitas untuk pemanggil FE-16 (`regenerateWorkflowContents`). */
export const regenerateWorkflowContents = regenerateContents;
