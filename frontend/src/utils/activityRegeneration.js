import { CONTENT_KIND } from '../services/contentService';
import { OPERATION_STATUS, OPERATION_TYPE } from '../services/executionService';
import { WORKFLOW_API_STATUS, isWorkflowBusy } from './workflowStatus';

/** Pemetaan OperationType eksekusi Moodle ke ContentKind konten AI workflow. */
export const OPERATION_TO_CONTENT_KIND = {
  [OPERATION_TYPE.LEARNING_MATERIAL]: CONTENT_KIND.LEARNING_MATERIAL,
  [OPERATION_TYPE.LEARNING_RESOURCE]: CONTENT_KIND.RESOURCE,
  [OPERATION_TYPE.ASSIGNMENT]: CONTENT_KIND.ASSIGNMENT,
  [OPERATION_TYPE.QUIZ]: CONTENT_KIND.QUIZ,
};

/**
 * Mencari operasi konten eksekusi yang menerbitkan course module `cmid` di Moodle.
 * Memprioritaskan operasi berstatus SUCCESS bila tersedia.
 */
export function findOperationForMoodleCm(executions = [], cmid) {
  if (!cmid || !Array.isArray(executions)) return null;
  const targetId = String(cmid);
  let fallback = null;

  for (const execution of executions) {
    for (const op of execution?.operations ?? []) {
      if (!op?.content_id || !OPERATION_TO_CONTENT_KIND[op.operation_type]) continue;
      if (String(op.moodle_object_id) !== targetId) continue;
      if (op.status === OPERATION_STATUS.SUCCESS) return op;
      if (!fallback) fallback = op;
    }
  }
  return fallback;
}

/**
 * Mencocokkan operasi eksekusi dengan record konten terbaru dari GET /workflows/{id}/contents
 * agar regenerasi ITEM selalu menggunakan versi paling mutakhir pada minggu & jenis terkait.
 */
export function resolveContentForOperation(contents = [], operation) {
  if (!operation) return null;
  const kind = OPERATION_TO_CONTENT_KIND[operation.operation_type] ?? null;
  const bySlot = Array.isArray(contents)
    ? contents.find((item) => item?.week_number === operation.week_number && (!kind || item?.kind === kind))
    : null;
  if (bySlot) return bySlot;

  const byId = Array.isArray(contents)
    ? contents.find((item) => item?.id === operation.content_id)
    : null;
  if (byId) return byId;

  if (!operation.content_id) return null;
  return {
    id: operation.content_id,
    week_number: operation.week_number,
    kind,
    title: operation.title,
  };
}

/**
 * Memeriksa apakah workflow mengizinkan regenerasi konten (WAITING_FOR_REVIEW atau FAILED sesuai BE-19.3).
 */
export function canRegenerateWorkflowContent(workflow) {
  if (!workflow) {
    return { allowed: false, reason: 'Workflow kursus belum ditemukan.' };
  }
  if (workflow.status === WORKFLOW_API_STATUS.COMPLETED) {
    return {
      allowed: false,
      reason: 'Workflow sudah berstatus selesai (COMPLETED) sehingga regenerasi dikunci oleh backend.',
    };
  }
  if (isWorkflowBusy(workflow)) {
    return {
      allowed: false,
      reason: 'Workflow sedang menjalankan proses lain. Tunggu hingga selesai sebelum meregenerasi.',
    };
  }
  return { allowed: true, reason: null };
}
