import { api } from './apiClient';

/**
 * Moodle Integration API (BE-04.7 / FE-09.1).
 * Seluruh komunikasi ke Moodle melewati Backend API gateway.
 */

/**
 * Cek status koneksi backend ke instance Moodle.
 * GET /api/v1/integrations/moodle/status
 *
 * @returns {Promise<{ status: 'CONNECTED' | 'DISCONNECTED', moodle_url: string, message?: string }>}
 */
export function getMoodleStatus() {
  return api.get('/integrations/moodle/status');
}

/**
 * Ambil daftar kursus dari Moodle LMS melalui backend adapter.
 * GET /api/v1/integrations/moodle/courses
 *
 * @returns {Promise<{ courses: Array<{ id: number, fullname: string, shortname: string, category?: string, summary?: string }> }>}
 */
export function getMoodleCourses() {
  return api.get('/integrations/moodle/courses');
}
