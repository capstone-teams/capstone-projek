import { api } from './apiClient';
import { isWorkflowBusy, isWorkflowFinished } from '../utils/workflowStatus';

// Monitoring workflow dan course target

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
const BINDING_STORAGE_KEY = 'agentic-lms.course-bindings';
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

/**
 * Membaca asosiasi kursus -> workflow & RPS aktif dari storage (FE-10 / FE-11 / RPS overwrite).
 * Menerima satu atau beberapa identifier (id, moodle_course_id, shortname) dan mengembalikan binding pertama yang cocok.
 */
export function getActiveCourseBinding(...courseIdentifiers) {
  const keys = courseIdentifiers.flat().filter(Boolean).map(String);
  if (keys.length === 0) return null;
  try {
    const raw = localStorage.getItem(BINDING_STORAGE_KEY) || sessionStorage.getItem(BINDING_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    for (const key of keys) {
      if (parsed[key]) return parsed[key];
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Menyimpan asosiasi kursus -> workflow & RPS aktif ke storage lokal & sesi.
 * Mendukung penyimpanan ke beberapa alias identifier sekaligus (mis. [2, "IF2230-SAMPLE"]).
 */
export function saveActiveCourseBinding(primaryKey, { workflowId, rpsId, pendingTargetSync }, aliases = []) {
  const keys = [primaryKey, ...aliases].flat().filter(Boolean).map(String);
  if (keys.length === 0) return;
  try {
    const read = () => {
      try {
        const raw = localStorage.getItem(BINDING_STORAGE_KEY) || sessionStorage.getItem(BINDING_STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
      } catch {
        return {};
      }
    };
    const bindings = read();
    const updatedAt = new Date().toISOString();
    for (const key of keys) {
      const nextPending = pendingTargetSync !== undefined
        ? Boolean(pendingTargetSync)
        : Boolean(bindings[key]?.pendingTargetSync);
      bindings[key] = {
        workflowId: workflowId ?? bindings[key]?.workflowId ?? null,
        rpsId: rpsId ?? bindings[key]?.rpsId ?? null,
        pendingTargetSync: nextPending,
        updated_at: updatedAt,
      };
    }
    const serialized = JSON.stringify(bindings);
    localStorage.setItem(BINDING_STORAGE_KEY, serialized);
    sessionStorage.setItem(BINDING_STORAGE_KEY, serialized);
  } catch {
    // Abaikan jika storage dinonaktifkan
  }
}

/**
 * Menghapus asosiasi kursus -> workflow & RPS aktif untuk satu kursus beserta aliasnya.
 */
export function clearActiveCourseBinding(...courseIdentifiers) {
  const keys = courseIdentifiers.flat().filter(Boolean).map(String);
  if (keys.length === 0) return;
  try {
    const raw = localStorage.getItem(BINDING_STORAGE_KEY) || sessionStorage.getItem(BINDING_STORAGE_KEY);
    if (!raw) return;
    const bindings = JSON.parse(raw);
    for (const key of keys) {
      delete bindings[key];
    }
    const serialized = JSON.stringify(bindings);
    localStorage.setItem(BINDING_STORAGE_KEY, serialized);
    sessionStorage.setItem(BINDING_STORAGE_KEY, serialized);
  } catch {
    // Abaikan jika storage dinonaktifkan
  }
}

/** Kosongkan simpanan course target (dipakai tes). */
export function clearWorkflowCache() {
  targetCache.clear();
  try {
    sessionStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(BINDING_STORAGE_KEY);
    sessionStorage.removeItem(BINDING_STORAGE_KEY);
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

/**
 * Nomor kursus Moodle dari data kursus: moodle_course_id (kursus dari backend, id-nya teks) atau id angka
 * (data Moodle). null bila kursus belum punya kursus Moodle; PUT moodle-target hanya menerima angka positif.
 */
export function moodleCourseIdOf(course) {
  const id = Number(course?.moodle_course_id ?? course?.id);
  return Number.isInteger(id) && id > 0 ? id : null;
}

/** PUT /workflows/{id}/moodle-target: id kursus memilih target, null melepaskannya. */
export function setMoodleTarget(workflowId, moodleCourseId) {
  return api.put(`/workflows/${workflowId}/moodle-target`, { moodle_course_id: moodleCourseId }).then((workflow) => {
    const stale = (key) => key.startsWith(`${workflowId}:`);
    [...targetCache.keys()].filter(stale).forEach((key) => targetCache.delete(key));
    writeStored((current) => Object.fromEntries(Object.entries(current).filter(([key]) => !stale(key))));
    if (moodleCourseId != null && workflow?.updated_at) {
      const key = `${workflowId}:${workflow.updated_at}`;
      targetCache.set(key, Promise.resolve(moodleCourseId));
      writeStored((current) => ({ ...current, [key]: moodleCourseId }));
    }
    return workflow;
  });
}

/** Seperti setMoodleTarget, tetapi id kursus dinormalisasi ke angka (dipakai halaman pemilihan course target). */
export function setWorkflowMoodleTarget(workflowId, moodleCourseId) {
  return setMoodleTarget(workflowId, moodleCourseId == null ? null : Number(moodleCourseId));
}

/**
 * Mengikat workflow baru ke kursus Moodle dan melepaskan seluruh workflow lama yang sebelumnya menargetkan kursus ini (overwrite).
 */
export async function bindWorkflowToCourse(newWorkflowId, moodleCourseId, { rpsId = null, aliases = [], throwOnError = false } = {}) {
  const keys = [moodleCourseId, ...aliases].flat().filter(Boolean).map(String);
  if (keys.length === 0) return null;

  const targetId = Number(moodleCourseId);
  const isNumeric = Number.isInteger(targetId) && targetId > 0;

  // Segera catat binding lokal agar transisi halaman langsung memakai workflow & RPS baru.
  // pendingTargetSync tetap true bila target numerik hingga workflow selesai berjalan dan terikat di server.
  saveActiveCourseBinding(keys[0], {
    workflowId: newWorkflowId,
    rpsId,
    pendingTargetSync: isNumeric,
  }, keys.slice(1));

  let updated = null;
  let bindError = null;
  if (isNumeric) {
    try {
      updated = await setWorkflowMoodleTarget(newWorkflowId, targetId);
    } catch (err) {
      bindError = err;
      console.warn('Gagal mengikat moodle-target di backend:', err);
    }

    try {
      const items = await listWorkflows();
      const targets = await Promise.all(items.map((item) => courseTargetOf(item)));
      for (let i = 0; i < items.length; i++) {
        if (items[i].id !== newWorkflowId && targets[i] === targetId) {
          await setWorkflowMoodleTarget(items[i].id, null).catch(() => null);
        }
      }
    } catch {
      // Abaikan jika pembersihan workflow lama gagal di backend
    }

    // Jika workflow sudah berhenti (mis. WAITING_FOR_REVIEW) saat target tersimpan, ikatan tidak akan tertimpa
    // lagi oleh runner background, sehingga pendingTargetSync dapat langsung ditandai selesai.
    if (updated && Number(updated.moodle_course_id) === targetId && !isWorkflowBusy(updated)) {
      saveActiveCourseBinding(keys[0], {
        workflowId: newWorkflowId,
        rpsId: rpsId ?? updated.rps_id,
        pendingTargetSync: false,
      }, keys.slice(1));
    }
  }

  if (throwOnError && bindError) throw bindError;
  return updated;
}

/**
 * Workflow kursus ini, dengan data terbaru dari GET /workflows/{id}; null bila tidak ada.
 * 1. Workflow yang course target-nya kursus ini di server (moodle_course_id): sumber bersama, sehingga setiap dosen
 *    yang membuka kursus melihat RPS dan workflow yang sama. Daftar terbaru lebih dulu.
 * 2. Bila server belum punya, binding di browser ini (mis. target gagal disimpan saat RPS diunggah).
 */
export async function findWorkflowForCourse(...courseIdentifiers) {
  const keys = courseIdentifiers.flat().filter(Boolean).map(String);
  if (keys.length === 0) return null;

  const numericId = keys.map(Number).find((n) => Number.isInteger(n) && n > 0);
  if (numericId) {
    const items = await listWorkflows();
    const targets = await Promise.all(items.map((item) => courseTargetOf(item)));
    const index = targets.findIndex((target) => target === numericId);
    if (index !== -1) return getWorkflow(items[index].id);
  }

  const binding = getActiveCourseBinding(...keys);
  if (!binding?.workflowId) return null;
  // Workflow tersimpan yang tidak dapat diambil (mis. sudah dihapus di backend) dianggap tidak ada.
  return getWorkflow(binding.workflowId).catch(() => null);
}
