import { api } from './apiClient';

// Integrasi Moodle lewat backend (/api/v1/integrations/moodle, src/schemas/moodle.py). Kegagalan diteruskan
// apa adanya supaya halaman menampilkan keadaan sebenarnya, bukan status atau daftar kursus pengganti.

/**
 * GET /integrations/moodle/status
 * @returns {Promise<{ status: string, connected: boolean, message: string, site_name: string, release: string,
 *   version: string, all_functions_available: boolean, functions: Array<{ name: string, available: boolean }> }>}
 */
export function getMoodleStatus() {
  return api.get('/integrations/moodle/status');
}

/** Kursus Moodle: `id` selalu angka dan sama dengan moodle_course_id, nilai yang dikirim ke PUT moodle-target. */
function toMoodleCourse(course) {
  return { ...course, id: course.moodle_course_id ?? course.id, summary: course.summary ?? '', category: course.category ?? null };
}

/**
 * GET /integrations/moodle/courses
 * @returns {Promise<{ courses: Array<{ id: number, moodle_course_id: number, fullname: string, shortname: string,
 *   visible: boolean, summary: string, category: string | null }> }>}
 */
export function getMoodleCourses() {
  return api.get('/integrations/moodle/courses').then((data) => ({ courses: (data?.courses ?? []).map(toMoodleCourse) }));
}
