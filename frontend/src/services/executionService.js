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

/** GET /workflows/{id}/executions: riwayat eksekusi, terbaru lebih dulu. */
export function listWorkflowExecutions(workflowId) {
  return api.get(`/workflows/${workflowId}/executions`).then((data) => data?.items ?? []);
}

/** GET /workflows/{id}/executions/{execution_id}: status, ringkasan, dan daftar operasi. */
export function getWorkflowExecution(workflowId, executionId) {
  return api.get(`/workflows/${workflowId}/executions/${executionId}`);
}

/** Eksekusi terbaru beserta operasinya; null bila workflow belum pernah dieksekusi. */
export async function getLatestWorkflowExecution(workflowId) {
  const [latest] = await listWorkflowExecutions(workflowId);
  return latest ? getWorkflowExecution(workflowId, latest.execution_id) : null;
}
