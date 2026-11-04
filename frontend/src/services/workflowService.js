import { api } from './apiClient';
<<<<<<< HEAD

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
=======
import { isWorkflowFinished } from '../utils/workflowStatus';

// Monitoring workflow dan course target

export function listWorkflows() {
  return api.get('/workflows').then((data) => data.items);
}

>>>>>>> develop
export function getWorkflow(workflowId) {
  return api.get(`/workflows/${workflowId}`);
}

<<<<<<< HEAD
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
=======
export function getWorkflowEvents(workflowId) {
  return api.get(`/workflows/${workflowId}/events`).then((data) => data.items);
}

// Course target tiap workflow yang sudah berhenti. Daftar GET /workflows tidak memuat moodle_course_id,
// jadi mencari workflow suatu kursus butuh GET /workflows/{id} untuk setiap workflow. Workflow yang sudah
// berhenti jarang berubah, sehingga hasilnya disimpan selama sesi, dengan kunci id + updated_at agar
// workflow yang dijalankan ulang diambil lagi. Promise disimpan agar permintaan yang sama tidak ganda, dan
// nilainya juga disimpan di sessionStorage supaya tidak hilang saat halaman dimuat ulang.
const STORAGE_KEY = 'agentic-lms.workflow-targets';
const targetCache = new Map();

function readStored() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY)) ?? {};
  } catch {
    return {};
  }
}

function writeStored(update) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(update(readStored())));
  } catch {
    // Penyimpanan sesi tidak tersedia (mis. jendela privat): cukup tanpa simpanan.
  }
}

/** Kosongkan simpanan course target (dipakai tes). */
export function clearWorkflowCache() {
  targetCache.clear();
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Tidak ada yang perlu dikosongkan.
  }
}

const cacheKey = (item) => `${item.id}:${item.updated_at}`;

function courseTargetOf(item) {
  if (!isWorkflowFinished(item)) return getWorkflow(item.id).then((workflow) => workflow.moodle_course_id ?? null);
  const key = cacheKey(item);
  const stored = readStored();
  if (key in stored) return Promise.resolve(stored[key]);
  if (!targetCache.has(key)) {
    targetCache.set(key, getWorkflow(item.id).then((workflow) => {
      const target = workflow.moodle_course_id ?? null;
      writeStored((current) => ({ ...current, [key]: target }));
      return target;
    }).catch((error) => {
      targetCache.delete(key);
      throw error;
    }));
  }
  return targetCache.get(key);
}

/** PUT /workflows/{id}/moodle-target: id kursus memilih target, null melepaskannya. */
export function setMoodleTarget(workflowId, moodleCourseId) {
  return api.put(`/workflows/${workflowId}/moodle-target`, { moodle_course_id: moodleCourseId }).then((workflow) => {
    const stale = (key) => key.startsWith(`${workflowId}:`);
    [...targetCache.keys()].filter(stale).forEach((key) => targetCache.delete(key));
    writeStored((current) => Object.fromEntries(Object.entries(current).filter(([key]) => !stale(key))));
    return workflow;
  });
}

/** Workflow yang menargetkan kursus ini, dengan data terbaru dari GET /workflows/{id}; null bila tidak ada. */
export async function findWorkflowForCourse(moodleCourseId) {
  const items = await listWorkflows();
  const targets = await Promise.all(items.map((item) => courseTargetOf(item)));
  const index = targets.findIndex((target) => target === Number(moodleCourseId));
  return index === -1 ? null : getWorkflow(items[index].id);
>>>>>>> develop
}
