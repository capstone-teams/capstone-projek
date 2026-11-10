import { api } from './apiClient';

// Konten mingguan berbasis workflow (BE-19.2 & BE-19.3, /api/v1/workflows/{workflow_id}/contents...).

/** Jenis konten hasil generation (backend src/services/content/domain.py: ContentKind). */
export const CONTENT_KIND = {
  LEARNING_MATERIAL: 'LEARNING_MATERIAL',
  RESOURCE: 'RESOURCE',
  ASSIGNMENT: 'ASSIGNMENT',
  QUIZ: 'QUIZ',
};

export const CONTENT_KIND_LABELS = {
  [CONTENT_KIND.LEARNING_MATERIAL]: 'Learning Material',
  [CONTENT_KIND.RESOURCE]: 'Learning Resource',
  [CONTENT_KIND.ASSIGNMENT]: 'Assignment',
  [CONTENT_KIND.QUIZ]: 'Quiz',
};

/** Status approval versi konten (ApprovalStatus backend). */
export const APPROVAL_STATUS = {
  DRAFT: 'DRAFT',
  VALIDATED: 'VALIDATED',
  PENDING_REVIEW: 'PENDING_REVIEW',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
  EXECUTED: 'EXECUTED',
};

/** Cakupan regenerasi konten (RegenerationScope backend). */
export const REGENERATION_SCOPE = {
  COURSE: 'COURSE',
  MINGGU: 'MINGGU',
  ITEM: 'ITEM',
};

/**
 * POST /api/v1/workflows/{workflow_id}/contents/generate
 * Memulai generation konten untuk seluruh minggu ('all') atau daftar nomor minggu ([1, 2, ...]).
 * Mengembalikan response 202 { workflow_id, status, scope, message }.
 */
export function generateWorkflowContents(workflowId, weeks = 'all') {
  return api.post(`/workflows/${workflowId}/contents/generate`, { weeks });
}

/**
 * GET /api/v1/workflows/{workflow_id}/contents
 * Mengambil versi terbaru setiap konten pada workflow (urut minggu).
 */
export function listWorkflowContents(workflowId, query) {
  return api.get(`/workflows/${workflowId}/contents`, query ? { query } : undefined)
    .then((res) => res?.items ?? []);
}

/**
 * GET /api/v1/workflows/{workflow_id}/contents/{content_id}
 * Mengambil detail satu versi konten beserta hasil validasinya.
 */
export function getWorkflowContent(workflowId, contentId) {
  return api.get(`/workflows/${workflowId}/contents/${contentId}`);
}

/**
 * POST /api/v1/workflows/{workflow_id}/contents/regenerate
 * Memulai regenerasi konten untuk scope COURSE, MINGGU, atau ITEM beserta catatan revisi wajib.
 */
export function regenerateWorkflowContents(
  workflowId,
  { scope = REGENERATION_SCOPE.ITEM, week_number, content_id, notes },
) {
  return api.post(`/workflows/${workflowId}/contents/regenerate`, {
    scope,
    ...(week_number != null ? { week_number } : {}),
    ...(content_id != null ? { content_id } : {}),
    notes,
  });
}
