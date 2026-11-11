import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ActivityRow from '../src/components/moodle/course/ActivityRow';
import { api } from '../src/services/apiClient';
import {
  getCoursesByClassification,
  getCourse,
  getCourseContents,
  getRecentCourses,
} from '../src/services/moodle/moodleApi';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe('Moodle Integrations API Courses Gateway', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('mengambil daftar kursus Moodle melalui GET /integrations/moodle/courses', async () => {
    const mockMoodleCourses = [
      {
        id: 2,
        moodle_course_id: 2,
        fullname: 'Pemrograman Web',
        shortname: 'IF2105',
        visible: true,
        summary: 'Pengembangan web modern',
        category_id: 1,
        category: 'Teknik Informatika',
      },
      {
        id: 3,
        moodle_course_id: 3,
        fullname: 'Basis Data',
        shortname: 'IF2203',
        visible: true,
        summary: 'Konsep basis data relasional',
        category_id: 1,
        category: 'Teknik Informatika',
      },
    ];

    const getSpy = vi.spyOn(api, 'get').mockImplementation(async (path) => {
      if (path === '/integrations/moodle/courses') {
        return { courses: mockMoodleCourses };
      }
      return null;
    });

    const courses = await getCoursesByClassification('all');
    expect(getSpy).toHaveBeenCalledWith('/integrations/moodle/courses');
    expect(courses).toHaveLength(2);
    expect(courses[0].shortname).toBe('IF2105');
    expect(courses[0].id).toBe(2);
    expect(courses[1].shortname).toBe('IF2203');
    expect(courses[1].id).toBe(3);
  });

  it('getRecentCourses menggunakan kursus dari GET /integrations/moodle/courses', async () => {
    vi.spyOn(api, 'get').mockImplementation(async (path) => {
      if (path === '/integrations/moodle/courses') {
        return {
          courses: [
            { id: 2, moodle_course_id: 2, fullname: 'Pemrograman Web', shortname: 'IF2105' },
          ],
        };
      }
      return null;
    });

    const recent = await getRecentCourses(3, 4);
    expect(recent).toHaveLength(1);
    expect(recent[0].fullname).toBe('Pemrograman Web');
  });

  it('getCourse mengambil detail kursus dari GET /integrations/moodle/courses/{id} untuk ID numerik', async () => {
    const getSpy = vi.spyOn(api, 'get').mockImplementation(async (path) => {
      if (path === '/integrations/moodle/courses/2') {
        return {
          id: 2,
          moodle_course_id: 2,
          fullname: 'Pemrograman Web',
          shortname: 'IF2105',
          summary: 'Deskripsi dari Moodle',
        };
      }
      return null;
    });

    const course = await getCourse(2);
    expect(getSpy).toHaveBeenCalledWith('/integrations/moodle/courses/2');
    expect(course.fullname).toBe('Pemrograman Web');
    expect(course.shortname).toBe('IF2105');
    expect(course.summary).toBe('Deskripsi dari Moodle');
  });

  it('getCourseContents mengambil section dan module dari GET /integrations/moodle/courses/{id}/contents', async () => {
    const getSpy = vi.spyOn(api, 'get').mockImplementation(async (path) => {
      if (path === '/integrations/moodle/courses/2/contents') {
        return {
          moodle_course_id: 2,
          sections: [
            {
              moodle_section_id: 10,
              section_number: 0,
              name: 'General',
              summary: 'Pengantar',
              visible: true,
              modules: [
                {
                  moodle_module_id: 101,
                  name: 'Pengumuman',
                  modname: 'forum',
                  visible: true,
                  description: 'Forum pengumuman',
                  content: null,
                },
              ],
            },
          ],
        };
      }
      return null;
    });

    const contents = await getCourseContents(2);
    expect(getSpy).toHaveBeenCalledWith('/integrations/moodle/courses/2/contents');
    expect(contents).toHaveLength(1);
    expect(contents[0].name).toBe('General');
    expect(contents[0].modules).toHaveLength(1);
    expect(contents[0].modules[0].name).toBe('Pengumuman');
  });

  it('tetap mendukung fallback ke /courses bila Moodle Integrations mengembalikan null atau kosong', async () => {
    vi.spyOn(api, 'get').mockImplementation(async (path) => {
      if (path === '/integrations/moodle/courses') {
        return { courses: [] };
      }
      if (path === '/courses') {
        return {
          items: [
            { id: 'IF2230-SAMPLE', shortname: 'IF2230-SAMPLE', fullname: 'Basis Data (Contoh)' },
          ],
        };
      }
      return null;
    });

    const courses = await getCoursesByClassification('all');
    expect(courses).toHaveLength(1);
    expect(courses[0].shortname).toBe('IF2230-SAMPLE');
  });

  it('melempar error jika Moodle Integrations dan /courses keduanya tidak mengembalikan data', async () => {
    vi.spyOn(api, 'get').mockImplementation(async (path) => {
      if (path === '/integrations/moodle/courses') {
        const err = new Error('502 Bad Gateway');
        err.status = 502;
        throw err;
      }
      if (path === '/courses') {
        return { items: [] };
      }
      return null;
    });

    await expect(getCoursesByClassification('all')).rejects.toThrow();
  });
});

describe('ActivityRow pada tampilan kursus', () => {
  let node;
  let root;

  beforeEach(() => {
    node = document.createElement('div');
    document.body.appendChild(node);
    root = createRoot(node);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    node.remove();
  });

  it('tidak menampilkan isi teks panjang assign/quiz/page di card kursus, tetapi tetap menampilkan petunjuk folder/label', async () => {
    await act(async () => root.render(
      <MemoryRouter>
        <ul>
          <ActivityRow
            courseId={2}
            isTeacher
            editMode={false}
            mod={{
              id: 101,
              name: 'Tugas 1 — Dasar Web',
              modname: 'assign',
              description: '<p>Instruksi lengkap tugas Bagian A dan Bagian B</p>',
              visible: 1,
              uservisible: true,
            }}
          />
          <ActivityRow
            courseId={2}
            isTeacher
            editMode={false}
            mod={{
              id: 102,
              name: 'Kuis 1',
              modname: 'quiz',
              description: '<p>Aturan pengerjaan kuis mingguan</p>',
              visible: 1,
              uservisible: true,
            }}
          />
          <ActivityRow
            courseId={2}
            isTeacher
            editMode={false}
            mod={{
              id: 103,
              name: 'Referensi Folder',
              modname: 'folder',
              description: '<p>Kumpulan berkas slide pertemuan 1</p>',
              visible: 1,
              uservisible: true,
            }}
          />
        </ul>
      </MemoryRouter>,
    ));

    expect(node.textContent).toContain('Tugas 1 — Dasar Web');
    expect(node.textContent).not.toContain('Instruksi lengkap tugas Bagian A dan Bagian B');
    expect(node.textContent).toContain('Kuis 1');
    expect(node.textContent).not.toContain('Aturan pengerjaan kuis mingguan');
    expect(node.textContent).toContain('Referensi Folder');
    expect(node.textContent).toContain('Kumpulan berkas slide pertemuan 1');

    const assignLink = [...node.querySelectorAll('a')].find((a) => a.textContent.includes('Tugas 1'));
    expect(assignLink?.getAttribute('href')).toBe('/course/2/mod/101');
  });
});
