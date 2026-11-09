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

/** GET /integrations/moodle/courses/{id}: satu kursus Moodle; 404 bila tidak ada di Moodle. */
export function getMoodleCourse(moodleCourseId) {
  return api.get(`/integrations/moodle/courses/${moodleCourseId}`).then(toMoodleCourse);
}

/**
 * GET /integrations/moodle/courses/{id}/contents: isi kursus yang sebenarnya ada di Moodle saat ini.
 * @returns {Promise<{ moodle_course_id: number, sections: Array<{ moodle_section_id: number, section_number: number,
 *   name: string, summary: string, visible: boolean, modules: Array<{ name: string, modname: string }> }> }>}
 */
export function getMoodleCourseContents(moodleCourseId) {
  return api.get(`/integrations/moodle/courses/${moodleCourseId}/contents`);
}

/**
 * POST /integrations/moodle/courses/{id}/sections: membuat section baru, atau mengganti nama section bila
 * `section_number` sudah ada (jadi aman diulang).
 */
export function saveMoodleSection(moodleCourseId, { name, section_number: sectionNumber }) {
  return api.post(`/integrations/moodle/courses/${moodleCourseId}/sections`, sectionNumber == null ? { name } : { name, section_number: sectionNumber });
}

/**
 * POST /integrations/moodle/courses: membuat kursus Moodle. Menurut backend hanya untuk pengujian (development),
 * sehingga tidak ditampilkan sebagai tombol bagi dosen.
 */
export function createMoodleCourse({ fullname, shortname, category_id: categoryId = 1 }) {
  return api.post('/integrations/moodle/courses', { fullname, shortname, category_id: categoryId }).then(toMoodleCourse);
}
