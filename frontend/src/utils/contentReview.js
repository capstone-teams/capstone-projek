// Review konten mingguan (FE-17): pengelompokan, temuan validasi, progres review, dan progres generation.
import { CONTENT_STATUS } from '../services/contentService';
import { WORKFLOW_API_STATUS, WORKFLOW_EVENT, WORKFLOW_STAGE, WORKFLOW_STATUS, workflowStatusOf } from './workflowStatus';

/** Konten dikelompokkan per minggu, urut nomor minggu; konten tanpa minggu di akhir. */
export function groupContentsByWeek(items = []) {
  const groups = new Map();
  items.forEach((item) => {
    const week = item.week_number ?? null;
    groups.set(week, [...(groups.get(week) ?? []), item]);
  });
  return [...groups.entries()]
    .sort(([a], [b]) => (a ?? Infinity) - (b ?? Infinity))
    .map(([week, contents]) => ({ week, contents }));
}

/**
 * Temuan validasi dari detail konten: `errors` dan `warnings` berbentuk { pemeriksaan: [pesan, ...] }.
 * Hasilnya [{ check, message, severity: 'error' | 'warning' }].
 */
export function validationFindings(validation) {
  const collect = (group, severity) => Object.entries(group ?? {}).flatMap(([check, messages]) => (Array.isArray(messages) ? messages : [messages])
    .filter(Boolean)
    .map((message) => ({ check, message: String(message), severity })));
  return [...collect(validation?.errors, 'error'), ...collect(validation?.warnings, 'warning')];
}

/** Konten dianggap sudah disetujui bila disetujui atau sudah dikirim ke Moodle. */
export const isContentApproved = (item) => [CONTENT_STATUS.APPROVED, CONTENT_STATUS.EXECUTED].includes(item?.status);

/** Progres review: { approved, total, complete } dari seluruh konten (bukan hanya yang lolos filter). */
export function reviewProgress(items = []) {
  const approved = items.filter(isContentApproved).length;
  return { approved, total: items.length, complete: items.length > 0 && approved === items.length };
}

/**
 * Alasan konten belum dapat disetujui (aturan approve backend), atau null bila dapat disetujui. Konten yang sudah
 * disetujui juga mengembalikan alasan agar tidak dikirim ulang.
 */
export function approvalBlocker(item) {
  if (isContentApproved(item)) return 'Konten sudah disetujui.';
  if (item?.status === CONTENT_STATUS.REJECTED) return 'Konten yang ditolak harus diregenerasi sebelum dapat disetujui.';
  if (item?.validation?.status !== 'PASSED') return 'Konten belum lolos validasi sehingga belum dapat disetujui.';
  return null;
}

export const isApprovable = (item) => approvalBlocker(item) === null;

/**
 * Tahap generation konten yang sedang berjalan: GENERATING_CONTENT, VALIDATING (validasi konten), atau RETRYING
 * pada tahap konten; null bila workflow tidak sedang membuat konten. VALIDATING juga dipakai course planning,
 * sehingga dibedakan dari tahap yang terakhir dimulai sebelumnya.
 */
export function contentGenerationProgressOf(workflow, events = []) {
  if (workflow?.status !== WORKFLOW_API_STATUS.RUNNING) return null;
  const status = workflowStatusOf(workflow);
  if (status === WORKFLOW_STATUS.GENERATING_CONTENT) return status;
  const lastStage = [...events].reverse().find((event) => event.event === WORKFLOW_EVENT.STAGE_STARTED && event.stage !== WORKFLOW_STAGE.VALIDATION)?.stage;
  if (lastStage !== WORKFLOW_STAGE.CONTENT_GENERATION) return null;
  if (status === WORKFLOW_STATUS.VALIDATING) return status;
  if (status === WORKFLOW_STATUS.RETRYING) return status;
  return null;
}
