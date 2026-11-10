/** Penanda minggu khusus (week_type, disalin backend dari RPS); minggu reguler tanpa penanda. */
export const WEEK_TYPE_LABELS = { uts: 'UTS', uas: 'UAS', kuis: 'Kuis', quiz: 'Kuis' };

/** Jenis aktivitas yang direncanakan pada course plan (CoursePlanActivityType backend). */
export const COURSE_PLAN_ACTIVITY_LABELS = {
  learning_material: 'Materi',
  learning_resource: 'Sumber belajar',
  assignment: 'Tugas',
  quiz: 'Kuis',
};

/** Apakah minggu tersebut minggu ujian (UTS/UAS) yang tidak menghasilkan konten pembelajaran. */
export function isExamWeek(week) {
  const type = String(week?.week_type ?? '').toLowerCase();
  return type === 'uts' || type === 'uas';
}

/** Label minggu khusus (UTS, UAS, Kuis) jika tersedia; null untuk minggu reguler. */
export function weekTypeLabel(week) {
  const type = String(week?.week_type ?? '').toLowerCase();
  return WEEK_TYPE_LABELS[type] ?? null;
}

/** Temuan validasi dikelompokkan: tingkat rencana (week kosong) lebih dulu, lalu per minggu berurutan. */
export function groupValidationIssues(issues = []) {
  const general = issues.filter((issue) => issue?.week == null);
  const byWeek = new Map();
  issues
    .filter((issue) => issue?.week != null)
    .sort((a, b) => a.week - b.week)
    .forEach((issue) => byWeek.set(issue.week, [...(byWeek.get(issue.week) ?? []), issue]));
  return { general, byWeek };
}
