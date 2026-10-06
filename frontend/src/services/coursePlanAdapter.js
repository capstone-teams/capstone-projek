import { ApiError } from './apiClient';

function invalidPlan() {
  return new ApiError(200, 'INVALID_RESPONSE', 'Struktur rencana kuliah tidak valid.');
}

function list(value) {
  if (value == null) return [];
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) throw invalidPlan();
  return value;
}

/** Course Plan Schema §8; pertahankan alias field untuk pemilih minggu dan konten. */
export function normalizeCoursePlan(data) {
  if (data == null) return null;
  if (!Array.isArray(data.weeks)) throw invalidPlan();
  const weeks = data.weeks.map((week) => {
    if (!week || typeof week !== 'object') throw invalidPlan();
    const number = week.week_number ?? week.week;
    if (!Number.isInteger(number) || number < 1) throw invalidPlan();
    const title = week.title ?? week.topic ?? '';
    if (typeof title !== 'string') throw invalidPlan();
    const objectives = list(week.objectives ?? week.learning_objectives);
    const topics = list(week.topics ?? week.sub_topics);
    const activities = list(week.planned_activities ?? week.activities);
    return {
      ...week,
      week_number: number,
      title,
      learning_outcomes: list(week.learning_outcomes),
      objectives,
      topics,
      teaching_methods: list(week.teaching_methods),
      planned_activities: activities,
      // GeneratePanel memilih minggu menggunakan field week/topic.
      week: number,
      topic: title,
      sub_topics: topics,
      learning_objectives: objectives,
    };
  });
  if (new Set(weeks.map((week) => week.week_number)).size !== weeks.length) throw invalidPlan();
  return { ...data, weeks: weeks.sort((a, b) => a.week_number - b.week_number) };
}
