/** Penanda minggu khusus (week_type, disalin backend dari RPS); minggu reguler tanpa penanda. */
export const WEEK_TYPE_LABELS = { uts: 'UTS', uas: 'UAS', kuis: 'Kuis' };

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
