import { api } from './apiClient';

// Eksekusi Moodle per workflow (BE-17.1/BE-17.2, /api/v1/workflows/{workflow_id}/executions...). Pada M03 cakupannya
// STRUCTURE: satu operasi SECTION per minggu course plan.

/** Jenis operasi eksekusi (OperationType backend). */
export const OPERATION_TYPE_LABELS = {
  SECTION: 'Section mingguan',
  LEARNING_MATERIAL: 'Materi',
  LEARNING_RESOURCE: 'Sumber belajar',
  ASSIGNMENT: 'Tugas',
  QUIZ: 'Kuis',
};

/** Status satu operasi (OperationStatus backend). */
export const OPERATION_STATUS_META = {
  PENDING: { label: 'Menunggu', tone: 'neutral' },
  RUNNING: { label: 'Berjalan', tone: 'info' },
  SUCCESS: { label: 'Berhasil', tone: 'success' },
  FAILED: { label: 'Gagal', tone: 'danger' },
  SKIPPED: { label: 'Dilewati', tone: 'neutral' },
};

/** Status satu run eksekusi (ExecutionStatus backend). */
export const EXECUTION_STATUS_META = {
  PENDING: { label: 'Menunggu', tone: 'neutral' },
  RUNNING: { label: 'Berjalan', tone: 'info' },
  SUCCESS: { label: 'Berhasil', tone: 'success' },
  FAILED: { label: 'Gagal', tone: 'danger' },
};

/**
 * Cakupan eksekusi Moodle (DL-012):
 * - STRUCTURE: Pembuatan struktur section 16 minggu sesuai course plan (M03).
 * - FULL: Pembuatan struktur beserta seluruh materi dan kuis (M04).
 */
export const EXECUTION_SCOPE = {
  STRUCTURE: 'STRUCTURE',
  FULL: 'FULL',
};

/**
 * Status siklus hidup eksekusi (backend src/schemas/execution.py).
 */
export const EXECUTION_STATUS = {
  PENDING: 'PENDING',
  RUNNING: 'RUNNING',
  SUCCESS: 'SUCCESS',
  FAILED: 'FAILED',
};

/**
 * Status operasi per minggu pada eksekusi Moodle.
 */
export const OPERATION_STATUS = {
  PENDING: 'PENDING',
  RUNNING: 'RUNNING',
  SUCCESS: 'SUCCESS',
  FAILED: 'FAILED',
  SKIPPED: 'SKIPPED',
};

/**
 * Jenis operasi yang dicatat eksekusi Moodle.
 */
export const OPERATION_TYPE = {
  SECTION: 'SECTION',
  LEARNING_MATERIAL: 'LEARNING_MATERIAL',
  LEARNING_RESOURCE: 'LEARNING_RESOURCE',
  ASSIGNMENT: 'ASSIGNMENT',
  QUIZ: 'QUIZ',
};

/**
 * Pesan ramah pengguna untuk kode penolakan prasyarat 409 (BE-17.1, FE-18.1).
 */
export const EXECUTION_PRECONDITION_ERRORS = {
  PLAN_NOT_APPROVED: 'Course plan versi terbaru belum disetujui dosen.',
  MOODLE_TARGET_NOT_SET: 'Mata kuliah target di Moodle belum dipilih.',
  MOODLE_UNAVAILABLE: 'Server Moodle sedang tidak dapat dijangkau oleh backend.',
  EXECUTION_IN_PROGRESS: 'Eksekusi struktur lain sedang berjalan pada alur kerja ini.',
  CONTENT_NOT_APPROVED: 'Masih ada konten jenis aktif yang belum disetujui pada tab Review.',
};

/**
 * Terjemahkan kode error penolakan prasyarat 409 (`error.details[0].message`) memakai peta kode alasan.
 * @param {any} error
 * @param {Record<string, string>} reasonMap
 * @param {string} fallbackMessage
 * @returns {string}
 */
export function formatPreconditionError(error, reasonMap, fallbackMessage) {
  const reasonCode = error?.details?.[0]?.message || error?.details?.[0]?.field;
  if (reasonCode && reasonMap?.[reasonCode]) {
    return reasonMap[reasonCode];
  }
  return error?.message || fallbackMessage;
}

/**
 * Terjemahkan kode error penolakan prasyarat eksekusi menjadi teks yang informatif.
 * @param {any} error
 * @returns {string}
 */
export function formatExecutionPreconditionError(error) {
  return formatPreconditionError(error, EXECUTION_PRECONDITION_ERRORS, 'Gagal memulai eksekusi ke Moodle.');
}

/**
 * POST /api/v1/workflows/{workflow_id}/executions
 * Memulai eksekusi struktur course plan mingguan ke Moodle.
 * @param {string} workflowId
 * @param {string} [scope='STRUCTURE']
 * @returns {Promise<import('./types').ExecutionResponse>}
 */
export function startExecution(workflowId, scope = EXECUTION_SCOPE.STRUCTURE) {
  return api.post(`/workflows/${workflowId}/executions`, { scope });
}

/**
 * GET /api/v1/workflows/{workflow_id}/executions
 * Mengambil riwayat eksekusi pada workflow ini, terbaru lebih dulu.
 * @param {string} workflowId
 * @returns {Promise<Array<any>>}
 */
export function listExecutions(workflowId) {
  return api.get(`/workflows/${workflowId}/executions`).then((res) => res?.items ?? (Array.isArray(res) ? res : []));
}

/**
 * GET /api/v1/workflows/{workflow_id}/executions/{execution_id}
 * Mengambil detail status eksekusi, ringkasan operasi mingguan, dan hasil read-back.
 * @param {string} workflowId
 * @param {string} executionId
 * @returns {Promise<any>}
 */
export function getExecution(workflowId, executionId) {
  return api.get(`/workflows/${workflowId}/executions/${executionId}`);
}

/**
 * POST /api/v1/workflows/{workflow_id}/executions/{execution_id}/retry
 * Mengulang hanya operasi-operasi yang gagal pada eksekusi sebelumnya.
 * @param {string} workflowId
 * @param {string} executionId
 * @returns {Promise<any>}
 */
export function retryExecution(workflowId, executionId) {
  return api.post(`/workflows/${workflowId}/executions/${executionId}/retry`);
}

/** Eksekusi terbaru beserta operasinya (monitoring workflow); null bila workflow belum pernah dieksekusi. */
export async function getLatestWorkflowExecution(workflowId) {
  const [latest] = await listExecutions(workflowId);
  return latest ? getExecution(workflowId, latest.execution_id) : null;
}
