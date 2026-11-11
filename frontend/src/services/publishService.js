import { approveContents } from './contentService';
import { EXECUTION_SCOPE, startExecution } from './executionService';
import { isApprovable, isContentApproved } from '../utils/contentReview';

/**
 * Ringkasan review akhir sebelum publikasi: konten yang akan disetujui, yang sudah disetujui, dan yang dilewati
 * (belum lolos validasi atau ditolak; eksekusi FULL mencatatnya sebagai SKIPPED).
 */
export function publishSummary(items = []) {
  const toApprove = items.filter(isApprovable);
  const approved = items.filter(isContentApproved);
  const skipped = items.filter((item) => !isApprovable(item) && !isContentApproved(item));
  return { toApprove, approved, skipped, publishable: toApprove.length + approved.length };
}

/**
 * Review akhir satu klik: setujui seluruh konten yang lolos validasi, lalu kirim struktur dan konten yang disetujui
 * ke Moodle (POST /workflows/{id}/executions scope FULL).
 */
export async function approveAndPublish(workflowId, items = []) {
  const { toApprove } = publishSummary(items);
  if (toApprove.length) await approveContents(workflowId, toApprove.map((item) => item.id));
  return startExecution(workflowId, EXECUTION_SCOPE.FULL);
}
