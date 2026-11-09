import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../src/services/apiClient';
import { clearWorkflowCache, findWorkflowForCourse, moodleCourseIdOf, setMoodleTarget } from '../src/services/workflowService';

const item = (id, status, updated = '2026-11-02T08:00:00Z') => ({ id, status, stage: null, rps_id: `rps-${id}`, created_at: updated, updated_at: updated });
const detail = (id, status, course = null, updated = '2026-11-02T08:00:00Z') => ({ ...item(id, status, updated), moodle_course_id: course });

describe('findWorkflowForCourse', () => {
  let list;
  let details;
  let gets;
  beforeEach(() => {
    clearWorkflowCache();
    list = [item('a', 'FAILED'), item('b', 'COMPLETED'), item('c', 'RUNNING')];
    details = { a: detail('a', 'FAILED'), b: detail('b', 'COMPLETED', 7), c: detail('c', 'RUNNING') };
    gets = vi.spyOn(api, 'get').mockImplementation(async (path) => {
      if (path === '/workflows') return { items: list };
      return details[path.split('/').pop()];
    });
  });
  afterEach(() => vi.restoreAllMocks());
  const detailCalls = () => gets.mock.calls.filter(([path]) => path !== '/workflows').map(([path]) => path.split('/').pop());

  it('menemukan workflow kursus lewat course target dan mengembalikan data terbarunya', async () => {
    expect(await findWorkflowForCourse(7)).toMatchObject({ id: 'b', moodle_course_id: 7 });
    expect(await findWorkflowForCourse(99)).toBeNull();
  });

  it('tidak mengambil ulang detail workflow yang sudah berhenti pada pencarian berikutnya', async () => {
    await findWorkflowForCourse(7);
    expect(detailCalls().sort()).toEqual(['a', 'b', 'b', 'c']); // tiap workflow sekali, ditambah detail terbaru yang cocok
    gets.mockClear();
    await findWorkflowForCourse(7);
    // Yang berhenti (a, b) dari simpanan; yang berjalan (c) selalu diambil; yang cocok (b) diambil segar.
    expect(detailCalls().sort()).toEqual(['b', 'c']);
  });

  it('simpanan bertahan walau halaman dimuat ulang (sessionStorage)', async () => {
    await findWorkflowForCourse(7);
    expect(Object.keys(JSON.parse(sessionStorage.getItem('agentic-lms.workflow-targets')))).toHaveLength(2);
    // Muat ulang halaman: simpanan memori hilang, sessionStorage tetap ada.
    const stored = sessionStorage.getItem('agentic-lms.workflow-targets');
    clearWorkflowCache();
    sessionStorage.setItem('agentic-lms.workflow-targets', stored);
    gets.mockClear();
    expect(await findWorkflowForCourse(7)).toMatchObject({ id: 'b' });
    expect(detailCalls().sort()).toEqual(['b', 'c']);
  });

  it('tetap berfungsi bila sessionStorage tidak dapat dipakai', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('diblokir'); });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('diblokir'); });
    expect(await findWorkflowForCourse(7)).toMatchObject({ id: 'b' });
  });

  it('permintaan serentak untuk workflow yang sama digabung', async () => {
    await Promise.all([findWorkflowForCourse(7), findWorkflowForCourse(7)]);
    expect(detailCalls().filter((id) => id === 'a')).toHaveLength(1);
  });

  it('mengambil ulang workflow yang berubah (updated_at baru), mis. dianalisis ulang', async () => {
    await findWorkflowForCourse(7);
    list = [item('a', 'FAILED', '2026-11-02T09:00:00Z'), item('b', 'COMPLETED'), item('c', 'RUNNING')];
    details.a = detail('a', 'FAILED', 7, '2026-11-02T09:00:00Z');
    expect(await findWorkflowForCourse(7)).toMatchObject({ id: 'a' });
  });

  it('mengosongkan simpanan workflow setelah course target diubah', async () => {
    await findWorkflowForCourse(7);
    vi.spyOn(api, 'put').mockResolvedValue(detail('b', 'COMPLETED', null));
    details.b = detail('b', 'COMPLETED', null);
    await setMoodleTarget('b', null);
    expect(await findWorkflowForCourse(7)).toBeNull();
  });

  it('kegagalan mengambil detail tidak tersimpan sehingga dicoba lagi', async () => {
    gets.mockImplementationOnce(async () => ({ items: list })).mockImplementationOnce(async () => { throw new Error('jaringan'); });
    await expect(findWorkflowForCourse(7)).rejects.toThrow('jaringan');
    gets.mockImplementation(async (path) => (path === '/workflows' ? { items: list } : details[path.split('/').pop()]));
    expect(await findWorkflowForCourse(7)).toMatchObject({ id: 'b' });
  });
});

describe('moodleCourseIdOf', () => {
  it('memakai moodle_course_id dari kursus backend (id teks), atau id angka dari data Moodle', () => {
    expect(moodleCourseIdOf({ id: '5AH7inFLxJDRKEa34saR9c', moodle_course_id: 42 })).toBe(42);
    expect(moodleCourseIdOf({ id: 'course_001', moodle_course_id: '2' })).toBe(2);
    expect(moodleCourseIdOf({ id: 3 })).toBe(3);
  });

  it('null bila kursus belum punya kursus Moodle (PUT moodle-target hanya menerima angka positif)', () => {
    expect(moodleCourseIdOf({ id: '5AH7inFLxJDRKEa34saR9c', moodle_course_id: null })).toBeNull();
    expect(moodleCourseIdOf({ id: 0 })).toBeNull();
    expect(moodleCourseIdOf(null)).toBeNull();
  });
});
