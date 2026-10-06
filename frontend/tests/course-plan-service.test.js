import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/services/config', () => ({ API_BASE_URL: '/api/v1', USE_MOCK: false, TOKEN_STORAGE_KEY: 'test.token' }));
const { getPlan } = await import('../src/services/courseService');

function response(data, status = 200) {
  const fetcher = vi.fn().mockResolvedValue({ ok: status < 400, status, text: async () => JSON.stringify(data) });
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}
afterEach(() => vi.unstubAllGlobals());

describe('Course Plan service contract', () => {
  it('reads schema fields and keeps content week selection compatible', async () => {
    const fetcher = response({
      course: { title: 'Basis Data', code: 'IF123', description: 'Pengantar basis data.' },
      weeks: [{ week_number: 2, title: 'Model data', learning_outcomes: ['LO-1'], objectives: ['OBJ-1'], topics: ['ERD'], teaching_methods: ['Diskusi'], planned_activities: ['assignment'] }],
    });
    const plan = await getPlan('project-1');
    expect(fetcher.mock.calls[0][0]).toBe('/api/v1/courses/project-1/plan');
    expect(plan.course.description).toBe('Pengantar basis data.');
    expect(plan.weeks[0]).toMatchObject({ week_number: 2, week: 2, title: 'Model data', topic: 'Model data', learning_outcomes: ['LO-1'], learning_objectives: ['OBJ-1'], teaching_methods: ['Diskusi'] });
  });

  it('accepts the previous response format without inventing missing outcomes or teaching methods', async () => {
    response({ version: 3, status: 'approved', weeks: [{ week: 1, topic: 'HTML', sub_topics: ['Semantik'], learning_objectives: ['Membuat dokumen'], planned_activities: ['learning_material'], note: 'Revisi' }] });
    const plan = await getPlan('project-1');
    expect(plan).toMatchObject({ version: 3, status: 'approved' });
    expect(plan.weeks[0]).toMatchObject({ week_number: 1, title: 'HTML', topics: ['Semantik'], objectives: ['Membuat dokumen'], learning_outcomes: [], teaching_methods: [], note: 'Revisi' });
  });

  it('uses canonical values when both formats are present and orders by RPS week number', async () => {
    response({ weeks: [{ week_number: 2, week: 99, title: 'Topik baru', topic: 'Topik lama', objectives: [], learning_objectives: ['lama'] }, { week_number: 1, title: 'Awal' }] });
    const plan = await getPlan('project-1');
    expect(plan.weeks.map((week) => week.week)).toEqual([1, 2]);
    expect(plan.weeks[1]).toMatchObject({ topic: 'Topik baru', learning_objectives: [] });
  });

  it.each([
    { weeks: null },
    { weeks: [{ week_number: 0 }] },
    { weeks: [{ week_number: 1, objectives: 'bukan array' }] },
    { weeks: [{ week_number: 1 }, { week_number: 1 }] },
  ])('rejects malformed plan data instead of showing an empty success: %j', async (data) => {
    response(data);
    await expect(getPlan('project-1')).rejects.toMatchObject({ code: 'INVALID_RESPONSE' });
  });

  it('keeps the distinction between a missing plan and an empty week list', async () => {
    response({ error: { code: 'RESOURCE_NOT_FOUND', message: 'Belum ada rencana.' } }, 404);
    await expect(getPlan('project-1')).rejects.toMatchObject({ status: 404 });
    response({ weeks: [] });
    await expect(getPlan('project-1')).resolves.toMatchObject({ weeks: [] });
  });
});
