import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MoodleSectionsCard from '../src/components/ai/course/MoodleSectionsCard';
import { normalizeCoursePlan } from '../src/services/coursePlanAdapter';

const plans = vi.hoisted(() => ({ getWorkflowPlan: vi.fn() }));
const courses = vi.hoisted(() => ({ getPlan: vi.fn() }));
const moodle = vi.hoisted(() => ({ saveMoodleSection: vi.fn() }));
const context = vi.hoisted(() => ({ course: {}, workflow: null, workflowId: null }));
vi.mock('../src/services/coursePlanService', async (original) => ({ ...(await original()), ...plans }));
vi.mock('../src/services/courseService', () => courses);
vi.mock('../src/services/moodleIntegrationService', () => moodle);
vi.mock('../src/hooks/useCourse', () => ({ useCourse: () => context }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const plan = (status) => normalizeCoursePlan({
  version: 1, status,
  weeks: [{ week_number: 1, title: 'Konsep basis data' }, { week_number: 2, title: 'ERD' }, { week_number: 3, title: 'Normalisasi' }],
});

let node;
let root;
beforeEach(() => {
  vi.resetAllMocks();
  context.course = { id: 'course-1' };
  context.workflow = { id: 'wf-1', status: 'COMPLETED', moodle_course_id: 42 };
  context.workflowId = 'wf-1';
  courses.getPlan.mockResolvedValue(null);
  node = document.createElement('div');
  document.body.appendChild(node);
});
afterEach(async () => {
  await act(async () => root?.unmount());
  root = null;
  node.remove();
});
async function render() {
  root ??= createRoot(node);
  await act(async () => root.render(<MemoryRouter><MoodleSectionsCard /></MemoryRouter>));
  await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
}
const pageButton = (text) => [...node.querySelectorAll('button')].find((b) => !b.closest('dialog') && b.textContent.trim() === text);
const dialogButton = (text) => [...node.querySelectorAll('dialog button')].find((b) => b.textContent.trim() === text);
const settle = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)));

describe('Section mingguan di Moodle (POST /integrations/moodle/courses/{id}/sections)', () => {
  it('tanpa course target mengarahkan ke tab Course Target', async () => {
    context.workflow = { id: 'wf-1', status: 'COMPLETED', moodle_course_id: null };
    plans.getWorkflowPlan.mockResolvedValue(plan('APPROVED'));
    await render();
    expect(node.textContent).toContain('Pilih course target terlebih dahulu.');
    expect(pageButton('Buat section mingguan')).toBeUndefined();
  });

  it('rencana yang belum disetujui: tombol nonaktif dengan keterangan', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan('DRAFT'));
    await render();
    expect(node.textContent).toContain('3 section (Minggu 1 sampai 3) di kursus Moodle #42');
    expect(pageButton('Buat section mingguan').disabled).toBe(true);
    expect(node.textContent).toContain('Tersedia setelah rencana course disetujui.');
  });

  it('rencana disetujui: setelah konfirmasi, satu section per minggu disimpan dengan nomor minggunya', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan('APPROVED'));
    moodle.saveMoodleSection.mockResolvedValue({ moodle_section_id: 1 });
    await render();
    await act(async () => pageButton('Buat section mingguan').click());
    expect(moodle.saveMoodleSection).not.toHaveBeenCalled(); // menunggu konfirmasi
    await act(async () => dialogButton('Ya, buat section').click());
    await settle();
    expect(moodle.saveMoodleSection.mock.calls).toEqual([
      [42, { name: 'Minggu 1: Konsep basis data', section_number: 1 }],
      [42, { name: 'Minggu 2: ERD', section_number: 2 }],
      [42, { name: 'Minggu 3: Normalisasi', section_number: 3 }],
    ]);
    expect(node.textContent).toContain('3 section tersimpan di Moodle.');
    expect(pageButton('Simpan ulang section').disabled).toBe(false);
  });

  it('kegagalan sebagian dilaporkan per minggu, section lain tetap disimpan', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan('APPROVED'));
    moodle.saveMoodleSection
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error('Layanan sedang tidak dapat diakses.'))
      .mockResolvedValueOnce({});
    await render();
    await act(async () => pageButton('Buat section mingguan').click());
    await act(async () => dialogButton('Ya, buat section').click());
    await settle();
    expect(moodle.saveMoodleSection).toHaveBeenCalledTimes(3);
    expect(node.textContent).toContain('1 section gagal disimpan');
    expect(node.textContent).toContain('Minggu 2: Layanan sedang tidak dapat diakses.');
  });

  it('tanpa course plan workflow memakai rencana project kursus', async () => {
    plans.getWorkflowPlan.mockResolvedValue(null);
    courses.getPlan.mockResolvedValue(plan('APPROVED'));
    await render();
    expect(courses.getPlan).toHaveBeenCalledWith('course-1');
    expect(pageButton('Buat section mingguan').disabled).toBe(false);
  });
});
