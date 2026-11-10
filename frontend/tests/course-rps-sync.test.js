import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../src/services/apiClient';
import { clearWorkflowCache, findWorkflowForCourse, saveActiveCourseBinding } from '../src/services/workflowService';

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
});
