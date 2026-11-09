import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CoursePlanPage from '../src/pages/dosen/ai/CoursePlanPage';
import { api, ApiError } from '../src/services/apiClient';
import { normalizeCoursePlan } from '../src/services/coursePlanAdapter';
import * as planApi from '../src/services/coursePlanService';

// Halaman Rencana memakai API course plan per workflow (BE-14). Layanan rencana diganti tiruan agar aturan
// backend (generate, approve/reject, regenerate, versi) dapat diatur per tes.
const plans = vi.hoisted(() => ({
  getWorkflowPlan: vi.fn(),
  generateWorkflowPlan: vi.fn(),
  approveWorkflowPlan: vi.fn(),
  rejectWorkflowPlan: vi.fn(),
  regenerateWorkflowPlan: vi.fn(),
  listWorkflowPlanVersions: vi.fn(),
  getWorkflowPlanVersion: vi.fn(),
}));
const courses = vi.hoisted(() => ({ getPlan: vi.fn() }));
const rpsApi = vi.hoisted(() => ({ getRps: vi.fn() }));
const context = vi.hoisted(() => ({ course: {}, workflow: null, workflowId: null, refresh: vi.fn() }));
vi.mock('../src/services/coursePlanService', async (original) => ({ ...(await original()), ...plans }));
vi.mock('../src/services/courseService', () => courses);
vi.mock('../src/services/rpsService', () => rpsApi);
vi.mock('../src/hooks/useCourse', () => ({ useCourse: () => context }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const plan = (overrides = {}) => normalizeCoursePlan({
  id: 'plan-1', workflow_id: 'wf-1', version: 2, status: 'DRAFT',
  course: { title: 'Basis Data', code: 'IF2230', description: 'Rencana sesuai RPS.' },
  validation: { passed: true, issues: [] },
  weeks: [{ week_number: 1, title: 'Model data', learning_outcomes: ['CPMK-1'], objectives: ['Membuat ERD'], topics: ['Entitas dan relasi'], teaching_methods: ['Diskusi'], planned_activities: ['assignment'], week_type: 'regular' }],
  ...overrides,
});
const waitingReview = { id: 'wf-1', status: 'RUNNING', stage: 'instructor_review', rps_id: 'rps-1', updated_at: '2026-11-06T08:00:00Z' };

let node;
let root;
beforeEach(() => {
  vi.resetAllMocks();
  context.course = { id: 'course-1', fullname: 'Basis Data', shortname: 'IF2230', rps_id: 'rps-1' };
  context.workflow = waitingReview;
  context.workflowId = 'wf-1';
  plans.listWorkflowPlanVersions.mockResolvedValue([]);
  rpsApi.getRps.mockResolvedValue({ id: 'rps-1', status: 'ANALYZED' });
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
  await act(async () => root.render(<MemoryRouter><CoursePlanPage /></MemoryRouter>));
  await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
}
// Tombol halaman, di luar <dialog> (Modal selalu ada di DOM; jsdom tidak membukanya).
const button = (text) => [...node.querySelectorAll('button')].find((b) => !b.closest('dialog') && b.textContent.trim() === text);
const dialog = (title) => [...document.querySelectorAll('dialog')].find((d) => d.querySelector('h2')?.textContent === title);
let openDialog = null;
const fillDialog = async (text) => {
  const area = dialog(openDialog).querySelector('textarea');
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(area, text);
    area.dispatchEvent(new Event('input', { bubbles: true }));
  });
};
const submitDialog = (label) => act(async () => [...dialog(openDialog).querySelectorAll('button')].find((b) => b.textContent.trim() === label).click());

describe('FE-05 halaman Rencana dengan API course plan per workflow', () => {
  it('menampilkan rencana terbaru dari GET /workflows/{id}/plan beserta identitas, status, dan versi', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan());
    await render();
    expect(plans.getWorkflowPlan).toHaveBeenCalledWith('wf-1');
    expect(node.textContent).toContain('Rencana course · versi 2');
    expect(node.textContent).toContain('Draft');
    expect(node.querySelector('[aria-label="Informasi rencana"]').textContent).toContain('IF2230');
    const row = node.querySelector('tbody tr');
    for (const text of ['Model data', 'Membuat ERD', 'Entitas dan relasi', 'Diskusi']) expect(row.textContent).toContain(text);
    expect(courses.getPlan).not.toHaveBeenCalled();
  });

  it('tanpa workflow: rencana project tampil sebagai bacaan, tanpa tombol generate', async () => {
    context.workflowId = null;
    context.workflow = null;
    courses.getPlan.mockResolvedValue(plan({ version: 1, status: 'PENDING_REVIEW' }));
    await render();
    expect(plans.getWorkflowPlan).not.toHaveBeenCalled();
    expect(courses.getPlan).toHaveBeenCalledWith('course-1');
    expect(node.textContent).toContain('Rencana course · versi 1');
    expect(node.textContent).toContain('Menunggu review');
    expect(node.textContent).toContain('Generate rencana tersedia setelah RPS kursus ini diproses dan dianalisis');
    expect(button('Generate rencana')).toBeUndefined();
    expect(button('Setujui rencana')).toBeUndefined();
  });

  it('tanpa workflow dan tanpa rencana project menampilkan keadaan kosong', async () => {
    context.workflowId = null;
    context.workflow = null;
    await render();
    expect(node.textContent).toContain('Rencana belum dibuat.');
  });

  it('belum ada course plan: Generate rencana memanggil POST /workflows/{id}/plan bila RPS sudah dianalisis', async () => {
    context.workflow = { ...waitingReview, status: 'COMPLETED', stage: null };
    plans.getWorkflowPlan.mockResolvedValue(null);
    plans.generateWorkflowPlan.mockResolvedValue({ workflow_id: 'wf-1', status: 'RUNNING', message: 'Dijadwalkan.' });
    await render();
    expect(node.textContent).toContain('Rencana belum dibuat.');
    expect(button('Generate rencana').disabled).toBe(false);
    await act(async () => button('Generate rencana').click());
    expect(plans.generateWorkflowPlan).toHaveBeenCalledWith('wf-1');
    expect(context.refresh).toHaveBeenCalled();
  });

  it('belum ada course plan dan RPS belum dianalisis: Generate nonaktif dengan alasan; rencana project tampil sebagai bacaan', async () => {
    context.workflow = { ...waitingReview, status: 'FAILED', stage: null };
    plans.getWorkflowPlan.mockResolvedValue(null);
    rpsApi.getRps.mockResolvedValue({ id: 'rps-1', status: 'FAILED' });
    courses.getPlan.mockResolvedValue(plan({ status: 'PENDING_REVIEW', version: 1 }));
    await render();
    expect(button('Generate rencana').disabled).toBe(true);
    expect(node.textContent).toContain('Tersedia setelah RPS kursus ini selesai dianalisis.');
    expect(courses.getPlan).toHaveBeenCalledWith('course-1');
    expect(node.textContent).toContain('Rencana tersimpan pada project kursus (hanya dibaca).');
    expect(node.textContent).toContain('Model data');
  });

  it('saat agent menyusun rencana menampilkan progres, bukan tombol generate', async () => {
    context.workflow = { ...waitingReview, stage: 'course_planning' };
    plans.getWorkflowPlan.mockResolvedValue(null);
    await render();
    expect(node.textContent).toContain('Agent sedang menyusun rencana');
    expect(button('Generate rencana')).toBeUndefined();
  });

  it('versi DRAFT saat workflow menunggu review: Setujui memanggil approve', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan());
    plans.approveWorkflowPlan.mockResolvedValue(plan({ status: 'APPROVED' }));
    await render();
    await act(async () => button('Setujui rencana').click());
    expect(plans.approveWorkflowPlan).toHaveBeenCalledWith('wf-1');
  });

  it('Tolak mewajibkan catatan revisi lalu memanggil reject dengan catatan itu', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan());
    plans.rejectWorkflowPlan.mockResolvedValue(plan({ status: 'REJECTED' }));
    await render();
    await act(async () => button('Tolak dengan catatan').click());
    openDialog = 'Tolak rencana';
    await submitDialog('Tolak rencana');
    expect(dialog('Tolak rencana').textContent).toContain('Catatan revisi wajib diisi.');
    expect(plans.rejectWorkflowPlan).not.toHaveBeenCalled();
    await fillDialog('Minggu 5-8 terlalu padat.');
    await submitDialog('Tolak rencana');
    expect(plans.rejectWorkflowPlan).toHaveBeenCalledWith('wf-1', 'Minggu 5-8 terlalu padat.');
  });

  it('versi DRAFT ketika workflow belum menunggu review: aksi review nonaktif dengan keterangan', async () => {
    context.workflow = { ...waitingReview, stage: 'validation' };
    plans.getWorkflowPlan.mockResolvedValue(plan());
    await render();
    expect(button('Setujui rencana').disabled).toBe(true);
    expect(button('Tolak dengan catatan').disabled).toBe(true);
    expect(node.textContent).toContain('Setujui atau tolak tersedia ketika workflow menunggu peninjauan Anda.');
  });

  it('rencana yang belum lolos validasi tidak dapat disetujui dan menampilkan temuannya', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan({ validation: { passed: false, issues: [{ message: 'Minggu 8 harus UTS.' }] } }));
    await render();
    expect(button('Setujui rencana').disabled).toBe(true);
    expect(node.textContent).toContain('Minggu 8 harus UTS.');
  });

  it('versi REJECTED: Regenerasi menerima prompt tambahan opsional (regenerate dengan instruction)', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan({ status: 'REJECTED', revision_notes: 'Terlalu padat.' }));
    plans.regenerateWorkflowPlan.mockResolvedValue({ workflow_id: 'wf-1', status: 'RUNNING', message: 'ok' });
    await render();
    expect(node.textContent).toContain('Ditolak');
    expect(node.textContent).toContain('Terlalu padat.');
    expect(button('Setujui rencana')).toBeUndefined();
    await act(async () => button('Regenerasi rencana').click());
    openDialog = 'Regenerasi rencana';
    await fillDialog('Tambahkan studi kasus kampus.');
    await submitDialog('Regenerasi rencana');
    expect(plans.regenerateWorkflowPlan).toHaveBeenCalledWith('wf-1', 'Tambahkan studi kasus kampus.');
  });

  it('regenerasi tanpa prompt tambahan tetap dapat dikirim', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan({ status: 'REJECTED' }));
    plans.regenerateWorkflowPlan.mockResolvedValue({ workflow_id: 'wf-1', status: 'RUNNING', message: 'ok' });
    await render();
    await act(async () => button('Regenerasi rencana').click());
    openDialog = 'Regenerasi rencana';
    await submitDialog('Regenerasi rencana');
    expect(plans.regenerateWorkflowPlan).toHaveBeenCalledWith('wf-1', '');
  });

  it('riwayat versi: memilih versi lama menampilkannya tanpa aksi review, lalu kembali ke terbaru', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan({ version: 2 }));
    plans.listWorkflowPlanVersions.mockResolvedValue([{ version: 2, status: 'DRAFT' }, { version: 1, status: 'REJECTED' }]);
    plans.getWorkflowPlanVersion.mockResolvedValue(plan({ version: 1, status: 'REJECTED', weeks: [{ week_number: 1, title: 'Versi lama' }] }));
    await render();
    await act(async () => button('v1').click());
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
    expect(plans.getWorkflowPlanVersion).toHaveBeenCalledWith('wf-1', 1);
    expect(node.textContent).toContain('Menampilkan versi 1');
    expect(node.textContent).toContain('Versi lama');
    expect(button('Setujui rencana')).toBeUndefined();
    await act(async () => button('Kembali ke versi terbaru').click());
    expect(node.textContent).toContain('Rencana course · versi 2');
  });

  it('versi APPROVED menampilkan konfirmasi dan tautan konten tanpa aksi review', async () => {
    context.workflow = { ...waitingReview, status: 'COMPLETED', stage: null };
    plans.getWorkflowPlan.mockResolvedValue(plan({ status: 'APPROVED' }));
    await render();
    expect(node.textContent).toContain('Rencana course telah disetujui');
    expect(button('Setujui rencana')).toBeUndefined();
    expect(button('Regenerasi rencana')).toBeUndefined();
  });

  it('gagal memuat menampilkan pesan dan pulih lewat Coba lagi', async () => {
    plans.getWorkflowPlan.mockRejectedValueOnce(new ApiError(503, 'INTERNAL_ERROR', 'Layanan sedang tidak dapat diakses.')).mockResolvedValueOnce(plan());
    await render();
    expect(node.querySelector('[role="alert"]').textContent).toContain('Layanan sedang tidak dapat diakses.');
    await act(async () => button('Coba lagi').click());
    expect(node.textContent).toContain('Model data');
  });
});

describe('coursePlanService memakai endpoint backend /workflows/{id}/plan', () => {
  const real = vi.importActual('../src/services/coursePlanService');
  afterEach(() => vi.restoreAllMocks());

  it('membaca, membuat, menyetujui, menolak, meregenerasi, dan membaca versi lewat jalur yang benar', async () => {
    const service = await real;
    const get = vi.spyOn(api, 'get').mockImplementation(async (path) => (path.endsWith('/versions') ? { items: [{ version: 1 }] } : plan()));
    const post = vi.spyOn(api, 'post').mockResolvedValue({});
    await service.getWorkflowPlan('wf-9');
    await service.listWorkflowPlanVersions('wf-9');
    await service.getWorkflowPlanVersion('wf-9', 3);
    await service.generateWorkflowPlan('wf-9');
    await service.approveWorkflowPlan('wf-9');
    await service.rejectWorkflowPlan('wf-9', 'catatan');
    await service.regenerateWorkflowPlan('wf-9', '  instruksi  ');
    await service.regenerateWorkflowPlan('wf-9', '   ');
    expect(get.mock.calls.map(([path]) => path)).toEqual(['/workflows/wf-9/plan', '/workflows/wf-9/plan/versions', '/workflows/wf-9/plan/versions/3']);
    expect(post.mock.calls).toEqual([
      ['/workflows/wf-9/plan'],
      ['/workflows/wf-9/plan/approve'],
      ['/workflows/wf-9/plan/reject', { notes: 'catatan' }],
      ['/workflows/wf-9/plan/regenerate', { instruction: 'instruksi' }],
      ['/workflows/wf-9/plan/regenerate', undefined],
    ]);
  });

  it('404 berarti workflow belum punya course plan (null); galat lain diteruskan', async () => {
    const service = await real;
    vi.spyOn(api, 'get').mockRejectedValueOnce(new ApiError(404, 'RESOURCE_NOT_FOUND', 'x'));
    expect(await service.getWorkflowPlan('wf-9')).toBeNull();
    vi.spyOn(api, 'get').mockRejectedValueOnce(new ApiError(500, 'INTERNAL_ERROR', 'y'));
    await expect(service.getWorkflowPlan('wf-9')).rejects.toMatchObject({ status: 500 });
  });

  it('status course plan backend punya label Indonesia', () => {
    expect(Object.keys(planApi.PLAN_STATUS_META)).toEqual(['DRAFT', 'VALIDATED', 'PENDING_REVIEW', 'APPROVED', 'REJECTED']);
    expect(planApi.MAX_PLAN_NOTE_LENGTH).toBe(2000);
  });
});
