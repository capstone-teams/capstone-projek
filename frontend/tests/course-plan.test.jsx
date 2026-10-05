import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CoursePlanPage from '../src/pages/ai/course/CoursePlanPage';
import { ApiError } from '../src/services/apiClient';
import { normalizeCoursePlan } from '../src/services/coursePlanAdapter';

const service = vi.hoisted(() => ({ getPlan: vi.fn(), generatePlan: vi.fn(), approvePlan: vi.fn(), regeneratePlan: vi.fn() }));
const context = vi.hoisted(() => ({ course: {}, version: 0, refresh: vi.fn() }));
vi.mock('../src/services/courseService', () => service);
vi.mock('../src/hooks/useCourse', () => ({ useCourse: () => context }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const fixture = () => normalizeCoursePlan({
  version: 2, status: 'draft', course: { title: 'Basis Data', code: 'IF123', credits: 3, description: 'Rencana sesuai RPS.' },
  learning_outcomes: [{ code: 'LO-1', description: 'Merancang basis data.' }],
  weeks: [{ week_number: 1, title: 'Model data', learning_outcomes: ['LO-1'], objectives: ['Membuat ERD'], topics: ['Entitas dan relasi'], teaching_methods: ['Diskusi'], planned_activities: ['assignment'] }],
});
let node, root;
beforeEach(() => {
  vi.resetAllMocks();
  context.course = { id: 'project-1', name: 'Basis Data', code: 'IF123', status: 'WAITING_PLAN_REVIEW' };
  context.version = 0;
  node = document.createElement('div');
  document.body.appendChild(node);
});
afterEach(async () => { await act(async () => root?.unmount()); root = null; node.remove(); });
async function render() { root ??= createRoot(node); await act(async () => root.render(<CoursePlanPage />)); }

describe('FE-05.1 Course Plan screen', () => {
  it('shows course information, outcomes, objectives, topics, methods, activities and status', async () => {
    service.getPlan.mockResolvedValue(fixture());
    await render();
    expect(node.querySelector('[aria-label="Informasi rencana"]').textContent).toContain('3 SKS');
    expect(node.textContent).toContain('Rencana sesuai RPS.');
    expect(node.textContent).toContain('Rencana course · versi 2');
    expect(node.textContent).toContain('Draft');
    const row = node.querySelector('tbody tr');
    for (const text of ['Model data', 'LO-1 — Merancang basis data.', 'Membuat ERD', 'Entitas dan relasi', 'Diskusi', 'Tugas']) expect(row.textContent).toContain(text);
    expect(node.querySelector('[aria-label="Minggu 1"]').textContent).toContain('Membuat ERD');
  });

  it('shows loading while the plan request is pending, then the result', async () => {
    let resolve;
    service.getPlan.mockReturnValue(new Promise((done) => { resolve = done; }));
    await render();
    expect(node.querySelector('[role="status"]').textContent).toContain('Memuat');
    await act(async () => resolve(fixture()));
    expect(node.querySelector('[role="status"]')).toBeNull();
    expect(node.textContent).toContain('Model data');
  });

  it.each([
    new Error('Layanan tidak tersedia.'),
    new ApiError(200, 'INVALID_RESPONSE', 'Struktur rencana kuliah tidak valid.'),
  ])('shows read error and recovers through Coba lagi: %s', async (error) => {
    service.getPlan.mockRejectedValueOnce(error).mockResolvedValueOnce(fixture());
    await render();
    expect(node.querySelector('[role="alert"]').textContent).toContain(error.message);
    expect(node.textContent).not.toContain('Rencana tidak ditemukan.');
    const retry = [...node.querySelectorAll('button')].find((button) => button.textContent === 'Coba lagi');
    await act(async () => retry.click());
    expect(node.querySelector('[role="alert"]')).toBeNull();
    expect(node.textContent).toContain('Model data');
  });

  it('shows CREATED as a genuine empty state without fetching or generating a plan', async () => {
    context.course.status = 'CREATED';
    await render();
    expect(node.textContent).toContain('Rencana belum dibuat.');
    expect(service.getPlan).not.toHaveBeenCalled();
    expect(service.generatePlan).not.toHaveBeenCalled();
  });

  it('shows progress when a plan is still being generated and has no result yet', async () => {
    context.course.status = 'PLANNING';
    service.getPlan.mockRejectedValue(new ApiError(404, 'RESOURCE_NOT_FOUND', 'Belum ada rencana.'));
    await render();
    expect(node.textContent).toContain('Agent sedang menyusun rencana');
    expect(node.textContent).toContain('Menyusun rencana…');
    expect(node.querySelector('[role="alert"]')).toBeNull();
  });

  it('shows a missing plan separately from a returned plan with no weeks', async () => {
    service.getPlan.mockRejectedValueOnce(new ApiError(404, 'RESOURCE_NOT_FOUND', 'Belum ada rencana.')).mockResolvedValueOnce(normalizeCoursePlan({ weeks: [] }));
    await render();
    expect(node.textContent).toContain('Rencana tidak ditemukan.');
    context.version += 1;
    await render();
    expect(node.textContent).toContain('Rencana mingguan belum tersedia.');
    expect(node.querySelector('table')).toBeNull();
  });

  it('keeps sparse data readable without inventing status, version or teaching methods', async () => {
    service.getPlan.mockResolvedValue(normalizeCoursePlan({ weeks: [{ week: 1, topic: 'HTML' }] }));
    await render();
    expect(node.textContent).toContain('Status belum tersedia');
    expect(node.textContent).not.toContain('versi undefined');
    expect(node.textContent).not.toContain('Draft');
    expect(node.querySelector('tbody tr').textContent).toContain('Belum tersedia.');
  });

  it('preserves the visible plan when a later refresh fails', async () => {
    service.getPlan.mockResolvedValueOnce(fixture()).mockRejectedValueOnce(new Error('Koneksi terputus.'));
    await render();
    context.version += 1;
    await render();
    expect(node.textContent).toContain('Model data');
    expect(node.querySelector('[role="alert"]').textContent).toContain('Koneksi terputus.');
  });
});
