import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../src/services/apiClient';
import { findCourseByMoodleId } from '../src/services/courseService';
import { getCourse, getCourseContents } from '../src/services/moodle/moodleApi';
import { isMoodleCourseId } from '../src/utils/courseId';

// Tanpa sesi Moodle di browser, kursus Moodle (ID angka) dibaca lewat /integrations/moodle/courses/{id}, bukan
// /courses/{id} yang hanya menerima ID project backend dan pasti menjawab 404.
vi.mock('../src/services/moodle/moodleClient', async (original) => ({
  ...(await original()),
  callWs: vi.fn().mockRejectedValue(new Error('tanpa sesi Moodle')),
}));

const paths = (spy) => spy.mock.calls.map(([path]) => path);

describe('ID kursus Moodle lewat Backend Gateway', () => {
  afterEach(() => vi.restoreAllMocks());

  it('membedakan ID kursus Moodle (angka) dari ID project backend', () => {
    expect(isMoodleCourseId(48)).toBe(true);
    expect(isMoodleCourseId('48')).toBe(true);
    expect(isMoodleCourseId('5AH7inFLxJDRKEa34saR9c')).toBe(false);
    expect(isMoodleCourseId(undefined)).toBe(false);
  });

  it('kursus Moodle: detail dan isi dari /integrations/moodle, tanpa memanggil /courses/{id}', async () => {
    const get = vi.spyOn(api, 'get').mockImplementation(async (path) => {
      if (path === '/integrations/moodle/courses/48') return { id: 48, fullname: 'Sistem Basis Data', shortname: 'SBD-2223', summary: 'Course uji.' };
      if (path === '/integrations/moodle/courses/48/contents') {
        return { moodle_course_id: 48, sections: [
          { moodle_section_id: 87, section_number: 0, name: 'General', summary: '', visible: true, modules: [{ moodle_module_id: 84, name: 'Announcements', modname: 'forum', visible: true, description: '' }] },
          { moodle_section_id: 88, section_number: 1, name: '', summary: '<p>Pengantar</p>', visible: false, modules: [] },
        ] };
      }
      throw new Error(`tidak diharapkan: ${path}`);
    });

    expect(await getCourse(48)).toMatchObject({ id: 48, shortname: 'SBD-2223', summary: 'Course uji.' });
    const sections = await getCourseContents(48);
    expect(sections).toEqual([
      { id: 87, section: 0, name: 'General', summary: '', summaryformat: 1, visible: 1, uservisible: true, modules: [{ id: 84, name: 'Announcements', modname: 'forum', description: '', content: null, visible: 1, uservisible: true }] },
      { id: 88, section: 1, name: 'Pertemuan 1', summary: '<p>Pengantar</p>', summaryformat: 1, visible: 0, uservisible: true, modules: [] },
    ]);
    expect(paths(get).some((path) => path.startsWith('/courses'))).toBe(false);
  });

  it('project kursus backend tetap memakai /courses/{id}/content dan /plan', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue(null);
    await getCourseContents('5AH7inFLxJDRKEa34saR9c');
    expect(paths(get)).toEqual(['/courses/5AH7inFLxJDRKEa34saR9c/content', '/courses/5AH7inFLxJDRKEa34saR9c/plan']);
  });

  it('kursus Moodle tanpa project generator: tidak memanggil /courses/{id}', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ items: [] });
    expect(await findCourseByMoodleId(48)).toBeNull();
    expect(paths(get)).toEqual(['/courses']);
  });
});
