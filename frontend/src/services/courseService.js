import { api } from './apiClient';
import { normalizeCoursePlan } from './coursePlanAdapter';

export function listCourses() {
  return api.get('/courses');
}

/**
 * Project generator milik satu kursus (satu kursus = satu project), atau null bila belum ada.
 * Hasil tetap disaring di sini supaya benar walau backend belum mendukung filter moodle_course_id.
 */
export async function findCourseByMoodleId(moodleCourseId) {
  if (!moodleCourseId) return null;
  const isNumeric = Number.isInteger(Number(moodleCourseId)) && Number(moodleCourseId) > 0;
  const res = await api.get('/courses', isNumeric ? { query: { moodle_course_id: moodleCourseId } } : undefined).catch(() => null);
  const list = res?.items ?? res?.courses ?? [];
  const found = list.find((c) =>
    (isNumeric && String(c.moodle_course_id) === String(moodleCourseId)) ||
    String(c.id) === String(moodleCourseId) ||
    String(c.shortname).toLowerCase() === String(moodleCourseId).toLowerCase()
  );
  // ID Moodle (angka) tanpa project terkait: /courses/{id} hanya menerima ID backend, jadi tidak perlu dipanggil.
  if (!found && isNumeric) return null;
  const detail = await api.get(`/courses/${found?.id ?? moodleCourseId}`).catch(() => null);
  return detail ?? found ?? null;
}

export function getCourse(courseId) {
  return api.get(`/courses/${courseId}`);
}

export function getPlan(courseId) {
  return api.get(`/courses/${courseId}/plan`).then(normalizeCoursePlan);
}

export function getContent(courseId, week) {
  return api.get(`/courses/${courseId}/content`, { query: { week } });
}
