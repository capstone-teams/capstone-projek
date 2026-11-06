import { api } from './apiClient';
import { normalizeCoursePlan } from './coursePlanAdapter';

// Course plan per workflow (BE-14, /api/v1/workflows/{workflow_id}/plan...). Aturan backend:
// - generate: RPS sudah ANALYZED dan workflow belum punya course plan (202, dikerjakan di belakang);
// - approve/reject: versi terbaru berstatus DRAFT saat workflow menunggu review; reject wajib catatan;
// - regenerate: hanya setelah versi terbaru REJECTED, dengan instruksi tambahan opsional;
// - setelah APPROVED tidak ada versi baru.

/** Status course plan (CoursePlanStatus backend). */
export const PLAN_STATUS = {
  DRAFT: 'DRAFT',
  VALIDATED: 'VALIDATED',
  PENDING_REVIEW: 'PENDING_REVIEW',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
};

export const PLAN_STATUS_META = {
  [PLAN_STATUS.DRAFT]: { label: 'Draft', tone: 'warning' },
  [PLAN_STATUS.VALIDATED]: { label: 'Tervalidasi', tone: 'info' },
  [PLAN_STATUS.PENDING_REVIEW]: { label: 'Menunggu review', tone: 'warning' },
  [PLAN_STATUS.APPROVED]: { label: 'Disetujui', tone: 'success' },
  [PLAN_STATUS.REJECTED]: { label: 'Ditolak', tone: 'danger' },
};

/** Batas catatan revisi dan instruksi regenerasi (MAX_REVISION_NOTES_LENGTH backend). */
export const MAX_PLAN_NOTE_LENGTH = 2000;

/** GET /workflows/{id}/plan: versi terbaru; null bila workflow belum punya course plan (404). */
export function getWorkflowPlan(workflowId) {
  return api.get(`/workflows/${workflowId}/plan`).then(normalizeCoursePlan, (error) => {
    if (error?.status === 404) return null;
    throw error;
  });
}

/** POST /workflows/{id}/plan: mulai penyusunan versi pertama. */
export function generateWorkflowPlan(workflowId) {
  return api.post(`/workflows/${workflowId}/plan`);
}

/** POST /workflows/{id}/plan/approve */
export function approveWorkflowPlan(workflowId) {
  return api.post(`/workflows/${workflowId}/plan/approve`);
}

/** POST /workflows/{id}/plan/reject: `notes` wajib diisi. */
export function rejectWorkflowPlan(workflowId, notes) {
  return api.post(`/workflows/${workflowId}/plan/reject`, { notes });
}

/** POST /workflows/{id}/plan/regenerate: `instruction` (prompt tambahan) opsional. */
export function regenerateWorkflowPlan(workflowId, instruction) {
  const cleaned = instruction?.trim();
  return api.post(`/workflows/${workflowId}/plan/regenerate`, cleaned ? { instruction: cleaned } : undefined);
}

/** GET /workflows/{id}/plan/versions: ringkasan semua versi, terbaru lebih dulu bila backend mengurutkannya. */
export function listWorkflowPlanVersions(workflowId) {
  return api.get(`/workflows/${workflowId}/plan/versions`).then((data) => data?.items ?? []);
}

/** GET /workflows/{id}/plan/versions/{version} */
export function getWorkflowPlanVersion(workflowId, version) {
  return api.get(`/workflows/${workflowId}/plan/versions/${version}`).then(normalizeCoursePlan);
}
