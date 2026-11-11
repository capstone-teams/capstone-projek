import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../src/services/apiClient';
import {
  bindWorkflowToCourse,
  clearWorkflowCache,
  findWorkflowForCourse,
  getActiveCourseBinding,
  saveActiveCourseBinding,
} from '../src/services/workflowService';

// RPS kursus harus sama bagi setiap dosen: course target di server (moodle_course_id) mengalahkan pilihan yang
// hanya tersimpan di browser (binding lokal), yang dipakai bila server belum punya course target.
const workflows = {
  'wf-sbd': { id: 'wf-sbd', status: 'RUNNING', stage: 'instructor_review', rps_id: 'rps-sbd', moodle_course_id: 48, updated_at: '2026-11-09T15:20:00Z' },
  'wf-mbd': { id: 'wf-mbd', status: 'RUNNING', stage: 'instructor_review', rps_id: 'rps-mbd', moodle_course_id: null, updated_at: '2026-11-09T15:10:00Z' },
};

function mockServer(targets) {
  vi.spyOn(api, 'get').mockImplementation(async (path) => {
    if (path === '/workflows') return { items: Object.values(workflows) };
    const id = path.split('/')[2];
    return { ...workflows[id], moodle_course_id: targets[id] ?? null };
  });
}

describe('sinkron RPS kursus antar dosen', () => {
  beforeEach(() => clearWorkflowCache());
  afterEach(() => vi.restoreAllMocks());

  it('course target di server didahulukan walau browser menyimpan RPS lain', async () => {
    saveActiveCourseBinding(48, { workflowId: 'wf-mbd', rpsId: 'rps-mbd' });
    mockServer({ 'wf-sbd': 48 });
    expect(await findWorkflowForCourse(48, 'SBD-2223')).toMatchObject({ id: 'wf-sbd', rps_id: 'rps-sbd' });
  });

  it('tanpa course target di server, RPS yang tersimpan di browser tetap dipakai', async () => {
    saveActiveCourseBinding(48, { workflowId: 'wf-mbd', rpsId: 'rps-mbd' });
    mockServer({});
    expect(await findWorkflowForCourse(48)).toMatchObject({ id: 'wf-mbd' });
  });

  it('tanpa course target dan tanpa pilihan di browser: tidak ada workflow', async () => {
    mockServer({});
    expect(await findWorkflowForCourse(48)).toBeNull();
  });

  it('bindWorkflowToCourse menyimpan pendingTargetSync saat masih berjalan dan menandainya selesai saat berhenti', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ items: [] });
    const putSpy = vi.spyOn(api, 'put')
      .mockResolvedValueOnce({ id: 'wf-new', status: 'RUNNING', stage: 'rps_analysis', moodle_course_id: 48, updated_at: '2026-11-11T08:00:00Z' })
      .mockResolvedValueOnce({ id: 'wf-new', status: 'RUNNING', stage: 'instructor_review', moodle_course_id: 48, updated_at: '2026-11-11T08:01:00Z' });

    await bindWorkflowToCourse('wf-new', 48, { rpsId: 'rps-new', aliases: ['SBD-2223'] });
    expect(getActiveCourseBinding(48)).toMatchObject({ workflowId: 'wf-new', rpsId: 'rps-new', pendingTargetSync: true });

    await bindWorkflowToCourse('wf-new', 48, { rpsId: 'rps-new', aliases: ['SBD-2223'] });
    expect(getActiveCourseBinding(48)).toMatchObject({ workflowId: 'wf-new', rpsId: 'rps-new', pendingTargetSync: false });
    expect(putSpy).toHaveBeenCalledTimes(2);
  });

  it('bindWorkflowToCourse melempar error bila throwOnError aktif dan PUT gagal', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ items: [] });
    vi.spyOn(api, 'put').mockRejectedValue(new Error('Gagal menyimpan'));

    await expect(bindWorkflowToCourse('wf-new', 48, { throwOnError: true })).rejects.toThrow('Gagal menyimpan');
    expect(getActiveCourseBinding(48)).toMatchObject({ workflowId: 'wf-new', pendingTargetSync: true });
  });
});
