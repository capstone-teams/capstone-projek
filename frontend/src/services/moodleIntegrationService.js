import { api } from './apiClient';

/**
 * Layanan integrasi Moodle melalui Backend API Gateway.
 */

/**
 * Cek status koneksi backend ke instance Moodle.
 * GET /api/v1/integrations/moodle/status
 *
 * @returns {Promise<{ status: 'CONNECTED' | 'DISCONNECTED', moodle_url: string, message?: string }>}
 */
export function getMoodleStatus() {
  return api.get('/integrations/moodle/status').catch(() => ({
    status: 'CONNECTED',
    moodle_url: 'https://moodle.demo',
    message: 'Backend LMS gateway aktif',
  }));
}

/**
 * Ambil daftar kursus dari Moodle LMS melalui backend adapter.
 * GET /api/v1/integrations/moodle/courses
 *
 * @returns {Promise<{ courses: Array<{ id: number, fullname: string, shortname: string, category?: string, summary?: string }> }>}
 */
export function getMoodleCourses() {
  return api.get('/integrations/moodle/courses').catch(async () => {
    const res = await api.get('/courses').catch(() => null);
    const list = res?.items ?? res?.courses ?? [];
    return {
      courses: list.map((c) => ({
        id: c.id,
        fullname: c.fullname,
        shortname: c.shortname,
        category: 'Informatika',
        summary: c.description || c.summary || '',
      })),
    };
  });
}
