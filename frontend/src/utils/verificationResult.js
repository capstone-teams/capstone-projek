import { EXECUTION_SCOPE, EXECUTION_STATUS } from '../services/executionService';
import {
  DISCREPANCY_TARGET_LABELS,
  DISCREPANCY_TYPE,
  DISCREPANCY_TYPE_LABELS,
  VERIFICATION_STATUS,
} from '../services/verificationService';

/** Filter daftar perbedaan verifikasi. */
export const DIFF_FILTER = {
  ALL: 'ALL',
  REMAINING: 'REMAINING',
  REPAIRED: 'REPAIRED',
};

/** Status perbaikan per temuan perbedaan verifikasi. */
export const REPAIR_STATUS = {
  REPAIRED: 'REPAIRED',
  UNEXPECTED_KEPT: 'UNEXPECTED_KEPT',
  REMAINING_REPAIRABLE: 'REMAINING_REPAIRABLE',
  MANUAL_ONLY: 'MANUAL_ONLY',
};

export const REPAIR_STATUS_META = {
  [REPAIR_STATUS.REPAIRED]: { label: 'Diperbaiki otomatis', tone: 'success' },
  [REPAIR_STATUS.UNEXPECTED_KEPT]: { label: 'Tambahan manual (dipertahankan)', tone: 'warning' },
  [REPAIR_STATUS.REMAINING_REPAIRABLE]: { label: 'Belum terperbaiki', tone: 'danger' },
  [REPAIR_STATUS.MANUAL_ONLY]: { label: 'Perlu perbaikan manual', tone: 'danger' },
};

/** Apakah hasil verifikasi menandakan course sesuai rencana (status PASS / matches true). */
export function isVerificationPassed(verification) {
  if (!verification) return false;
  return verification.matches === true || verification.status === VERIFICATION_STATUS.PASS;
}

/** Mengambil eksekusi FULL terbaru yang sudah selesai (SUCCESS / FAILED) sebagai target verifikasi default. */
export function findLatestFinishedFullExecution(executions = []) {
  if (!Array.isArray(executions)) return null;
  return executions.find(
    (ex) => ex?.scope === EXECUTION_SCOPE.FULL
      && (ex.status === EXECUTION_STATUS.SUCCESS || ex.status === EXECUTION_STATUS.FAILED),
  ) ?? null;
}

/** Apakah workflow masih memiliki eksekusi yang sedang berjalan (PENDING / RUNNING). */
export function hasRunningExecution(executions = []) {
  if (!Array.isArray(executions)) return false;
  return executions.some(
    (ex) => ex?.status === EXECUTION_STATUS.PENDING || ex?.status === EXECUTION_STATUS.RUNNING,
  );
}

function deriveRepairState(item, source) {
  if (source === 'repaired') return REPAIR_STATUS.REPAIRED;
  if (item?.type === DISCREPANCY_TYPE.UNEXPECTED) return REPAIR_STATUS.UNEXPECTED_KEPT;
  return item?.repairable ? REPAIR_STATUS.REMAINING_REPAIRABLE : REPAIR_STATUS.MANUAL_ONLY;
}

function summarizeSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== 'object') return null;
  if (snapshot.title) return snapshot.title;
  if (snapshot.name) return snapshot.name;
  if (snapshot.section != null) return `Minggu ${snapshot.section}`;
  if (snapshot.modname) return `Module ${snapshot.modname}`;
  if (snapshot.moodle_object_id != null) return `ID #${snapshot.moodle_object_id}`;
  return null;
}

function formatObjectTitle(item) {
  return summarizeSnapshot(item?.expected) || summarizeSnapshot(item?.actual) || null;
}

function normalizeDiffEntry(item, source, index) {
  const repairState = deriveRepairState(item, source);
  const typeLabel = DISCREPANCY_TYPE_LABELS[item?.type] || item?.label || item?.type || 'Perbedaan';
  const targetLabel = DISCREPANCY_TARGET_LABELS[item?.target] || item?.target || 'Objek Moodle';
  const expectedText = summarizeSnapshot(item?.expected);
  const actualText = summarizeSnapshot(item?.actual);

  return {
    ...item,
    key: `${source}-${item?.week_number ?? 'none'}-${item?.operation_id ?? item?.moodle_object_id ?? index}-${index}`,
    source,
    repairState,
    repairMeta: REPAIR_STATUS_META[repairState],
    typeLabel,
    targetLabel,
    objectTitle: formatObjectTitle(item),
    expectedText,
    actualText,
  };
}

/**
 * Menggabungkan perbedaan tersisa (`discrepancies`) dan perbedaan yang sudah diperbaiki (`repaired`),
 * mengurutkan per minggu (minggu `null` di bagian akhir), serta menyaring sesuai filter aktif.
 */
export function collectVerificationDiffs(verification, filter = DIFF_FILTER.ALL) {
  if (!verification) return [];
  const remaining = (verification.discrepancies ?? []).map((item, idx) =>
    normalizeDiffEntry(item, 'remaining', idx),
  );
  const repaired = (verification.repaired ?? []).map((item, idx) =>
    normalizeDiffEntry(item, 'repaired', idx),
  );

  let combined;
  if (filter === DIFF_FILTER.REMAINING) {
    combined = remaining;
  } else if (filter === DIFF_FILTER.REPAIRED) {
    combined = repaired;
  } else {
    combined = [...remaining, ...repaired];
  }

  return combined.sort((a, b) => {
    const wa = a.week_number ?? Number.MAX_SAFE_INTEGER;
    const wb = b.week_number ?? Number.MAX_SAFE_INTEGER;
    if (wa !== wb) return wa - wb;
    // Pada minggu yang sama, tampilkan sisa perbedaan terlebih dulu baru yang sudah diperbaiki.
    if (a.source !== b.source) return a.source === 'remaining' ? -1 : 1;
    return 0;
  });
}

/**
 * Mengelompokkan daftar perbedaan verifikasi per `week_number` sambil mempertahankan urutan mingguan.
 */
export function groupVerificationDiffsByWeek(verification, filter = DIFF_FILTER.ALL) {
  const entries = collectVerificationDiffs(verification, filter);
  const byWeek = new Map();
  for (const entry of entries) {
    const weekKey = entry.week_number ?? null;
    if (!byWeek.has(weekKey)) byWeek.set(weekKey, []);
    byWeek.get(weekKey).push(entry);
  }
  return [...byWeek.entries()].map(([weekNumber, items]) => ({ weekNumber, items }));
}
