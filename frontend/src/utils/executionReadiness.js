import { CONTENT_KIND } from '../services/contentService';
import { EXECUTION_SCOPE, OPERATION_TYPE } from '../services/executionService';
import { isContentApproved } from './contentReview';

/** Pemetaan kunci Activity Configuration dosen ke ContentKind backend/frontend. */
export const ACTIVITY_TYPE_TO_CONTENT_KIND = {
  learning_material: CONTENT_KIND.LEARNING_MATERIAL,
  learning_resource: CONTENT_KIND.RESOURCE,
  assignment: CONTENT_KIND.ASSIGNMENT,
  quiz: CONTENT_KIND.QUIZ,
};

export const CONTENT_KIND_ORDER = [
  CONTENT_KIND.LEARNING_MATERIAL,
  CONTENT_KIND.RESOURCE,
  CONTENT_KIND.ASSIGNMENT,
  CONTENT_KIND.QUIZ,
];

const OPERATION_TYPE_ORDER = [
  OPERATION_TYPE.SECTION,
  OPERATION_TYPE.LEARNING_MATERIAL,
  OPERATION_TYPE.LEARNING_RESOURCE,
  OPERATION_TYPE.ASSIGNMENT,
  OPERATION_TYPE.QUIZ,
];

function kindSortIndex(kind) {
  const idx = CONTENT_KIND_ORDER.indexOf(kind);
  return idx === -1 ? CONTENT_KIND_ORDER.length : idx;
}

function operationSortIndex(type) {
  const idx = OPERATION_TYPE_ORDER.indexOf(type);
  return idx === -1 ? OPERATION_TYPE_ORDER.length : idx;
}

/**
 * Mengembalikan himpunan ContentKind aktif dari konfigurasi aktivitas dosen.
 * Bila konfigurasi tidak tersedia atau kosong, seluruh ContentKind dianggap aktif.
 */
export function activeContentKindsOf(setup) {
  const enabled = setup?.activity?.enabled_activity_types;
  if (!Array.isArray(enabled) || enabled.length === 0) {
    return new Set(CONTENT_KIND_ORDER);
  }
  const mapped = enabled
    .map((key) => ACTIVITY_TYPE_TO_CONTENT_KIND[key])
    .filter(Boolean);
  return mapped.length > 0 ? new Set(mapped) : new Set(CONTENT_KIND_ORDER);
}

/**
 * Mengevaluasi prasyarat approval konten jenis aktif untuk eksekusi cakupan FULL (FE-18.1).
 */
export function evaluateContentApprovalReadiness(contents = [], setup = null) {
  const activeKinds = activeContentKindsOf(setup);
  const allContents = Array.isArray(contents) ? contents : [];
  const activeItems = allContents
    .filter((item) => item?.kind && activeKinds.has(item.kind))
    .sort((a, b) => {
      const weekDiff = (a.week_number ?? Infinity) - (b.week_number ?? Infinity);
      if (weekDiff !== 0) return weekDiff;
      return kindSortIndex(a.kind) - kindSortIndex(b.kind);
    });

  const approvedItems = [];
  const unapprovedItems = [];
  const countsByKind = {
    [CONTENT_KIND.LEARNING_MATERIAL]: 0,
    [CONTENT_KIND.RESOURCE]: 0,
    [CONTENT_KIND.ASSIGNMENT]: 0,
    [CONTENT_KIND.QUIZ]: 0,
  };

  for (const item of activeItems) {
    if (countsByKind[item.kind] !== undefined) {
      countsByKind[item.kind] += 1;
    }
    if (isContentApproved(item)) {
      approvedItems.push(item);
    } else {
      unapprovedItems.push(item);
    }
  }

  return {
    hasAnyContent: allContents.length > 0,
    hasActiveContents: activeItems.length > 0,
    allApproved: activeItems.length > 0 && unapprovedItems.length === 0,
    activeCount: activeItems.length,
    approvedCount: approvedItems.length,
    unapprovedItems,
    countsByKind,
    activeKinds,
  };
}

/** Apakah eksekusi menggunakan cakupan FULL atau memiliki operasi non-SECTION. */
export function isFullScopeExecution(execution) {
  if (!execution) return false;
  if (execution.scope === EXECUTION_SCOPE.FULL) return true;
  return (execution.operations ?? []).some(
    (op) => op?.operation_type && op.operation_type !== OPERATION_TYPE.SECTION,
  );
}

/**
 * Mengelompokkan operasi eksekusi per minggu (SECTION + seluruh activity di minggu tsb).
 */
export function groupExecutionOperationsByWeek(operations = [], plan = null) {
  const planWeekTitles = new Map(
    (plan?.weeks ?? []).map((w) => [w.week_number, w.title]),
  );

  const byWeek = new Map();
  const unscheduledOperations = [];
  let maxOpWeek = 0;

  for (const op of operations) {
    const weekNum = op?.week_number;
    if (weekNum == null) {
      unscheduledOperations.push(op);
      continue;
    }
    const numericWeek = Number(weekNum);
    if (numericWeek > maxOpWeek) maxOpWeek = numericWeek;
    const list = byWeek.get(numericWeek) ?? [];
    list.push(op);
    byWeek.set(numericWeek, list);
  }

  const maxPlanWeek = Math.max(
    plan?.weeks?.length || 0,
    ...(plan?.weeks ?? []).map((w) => Number(w?.week_number) || 0),
  );
  const totalWeeks = Math.max(maxOpWeek, maxPlanWeek || 16);

  const weeks = Array.from({ length: totalWeeks }, (_, idx) => {
    const weekNumber = idx + 1;
    const weekOps = [...(byWeek.get(weekNumber) ?? [])].sort(
      (a, b) => operationSortIndex(a?.operation_type) - operationSortIndex(b?.operation_type),
    );
    return {
      weekNumber,
      title: planWeekTitles.get(weekNumber) || `Topik Perkuliahan Minggu ${weekNumber}`,
      operations: weekOps,
    };
  });

  return { weeks, unscheduledOperations };
}
