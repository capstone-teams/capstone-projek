import { api } from './apiClient';
import { isWorkflowFinished } from '../utils/workflowStatus';

// Monitoring workflow dan course target (design-api §16, BE-11.3).

export function listWorkflows() {
  return api.get('/workflows').then((data) => data.items);
}

export function getWorkflow(workflowId) {
  return api.get(`/workflows/${workflowId}`);
}

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
}
