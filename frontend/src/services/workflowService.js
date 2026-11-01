import { api } from './apiClient';

/**
 * Workflow API (design-api.md §16, BE-11.3 / FE-09.2).
 * Monitoring proses dan pengaitan target Moodle ke alur kerja agent.
 */

/**
 * Ambil daftar workflow milik dosen yang login.
 * GET /api/v1/workflows
 *
 * @returns {Promise<{ items: Array<{ id: string, status: string, stage: string | null, progress: { completed: number, total: number }, rps_id: string | null, created_at: string, updated_at: string }> }>}
 */
export function listWorkflows() {
  return api.get('/workflows');
}

/**
 * Ambil status detail satu workflow beserta target kursus Moodle yang tersimpan.
 * GET /api/v1/workflows/{workflow_id}
 *
 * @param {string} workflowId
 * @returns {Promise<{ id: string, status: string, stage: string | null, progress: { completed: number, total: number }, rps_id: string | null, moodle_course_id: number | null, created_at: string, updated_at: string }>}
 */
export function getWorkflow(workflowId) {
  return api.get(`/workflows/${workflowId}`);
}

/**
 * Simpan target kursus Moodle pada workflow (FE-09.2, BE-11.3).
 * PUT /api/v1/workflows/{workflow_id}/moodle-target
 *
 * @param {string} workflowId
 * @param {number | null} moodleCourseId - ID kursus di Moodle atau null untuk mengosongkan.
 * @returns {Promise<{ id: string, moodle_course_id: number | null, ... }>}
 */
export function setWorkflowMoodleTarget(workflowId, moodleCourseId) {
  return api.put(`/workflows/${workflowId}/moodle-target`, {
    moodle_course_id: moodleCourseId == null ? null : Number(moodleCourseId),
  });
}

/**
 * Ambil riwayat event workflow (HTTP fallback untuk event WebSocket).
 * GET /api/v1/workflows/{workflow_id}/events
 *
 * @param {string} workflowId
 * @returns {Promise<{ items: Array<Object> }>}
 */
export function getWorkflowEvents(workflowId) {
  return api.get(`/workflows/${workflowId}/events`);
}
