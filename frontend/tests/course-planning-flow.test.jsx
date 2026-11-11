import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CoursePlanPage from '../src/pages/dosen/ai/CoursePlanPage';
import CourseRpsPage from '../src/pages/dosen/ai/CourseRpsPage';
import { ApiError } from '../src/services/apiClient';
import { normalizeCoursePlan } from '../src/services/coursePlanAdapter';
import { applyWorkflowEvent, coursePlanFailureOf, coursePlanProgressOf } from '../src/utils/workflowStatus';

const sampleRpsStructuredData = () => ({
  course: { name: 'Basis Data', code: 'IF2230', credits: 3, semester: 4, description: 'Perancangan basis data.' },
  cpl: [{ code: 'CPL-1', description: 'Mampu merancang sistem basis data.' }],
  cpmk: [{ code: 'CPMK-1', description: 'Memahami model data relasional.' }],
  sub_cpmk: [{ code: 'SUB-1', description: 'Membuat diagram ERD.' }],
  weeks: [{ week: 1, week_type: 'regular', topics: ['Model data'], cpmk: ['CPMK-1'], sub_cpmk: ['SUB-1'], teaching_method: ['Diskusi'], media: ['Slide'], assessment: null }],
  references: ['Elmasri & Navathe'],
  warnings: [],
});

// FE-12.1: memulai course planning dari Hasil Analisis RPS, progres lewat event workflow, rencana tampil
// otomatis saat workflow menunggu review, hasil validasi, dan kegagalan yang dapat dicoba ulang.
const plans = vi.hoisted(() => ({
  getWorkflowPlan: vi.fn(),
  generateWorkflowPlan: vi.fn(),
  approveWorkflowPlan: vi.fn(),
  rejectWorkflowPlan: vi.fn(),
  regenerateWorkflowPlan: vi.fn(),
  listWorkflowPlanVersions: vi.fn(),
  getWorkflowPlanVersion: vi.fn(),
}));
const rpsApi = vi.hoisted(() => ({ getRps: vi.fn(), getRpsAnalysis: vi.fn(), processRps: vi.fn(), reanalyzeRps: vi.fn(), listRps: vi.fn() }));
const context = vi.hoisted(() => ({ course: {}, workflow: null, workflowId: null, events: [], refresh: vi.fn() }));
const monitors = vi.hoisted(() => ({ byId: {}, reload: vi.fn() }));
vi.mock('../src/services/coursePlanService', async (original) => ({ ...(await original()), ...plans }));
vi.mock('../src/services/courseService', () => ({ getPlan: vi.fn().mockResolvedValue(null), findCourseByMoodleId: vi.fn() }));
vi.mock('../src/services/rpsService', () => rpsApi);
vi.mock('../src/hooks/useCourse', () => ({ useCourse: () => context }));
vi.mock('../src/hooks/useWorkflowMonitor', () => ({
  useWorkflowMonitor: (id) => ({ workflow: null, events: [], connection: 'connected', loading: false, error: null, ...(id ? monitors.byId[id] : {}), reload: monitors.reload }),
}));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const plan = (overrides = {}) => normalizeCoursePlan({
  id: 'plan-1', workflow_id: 'wf-1', version: 1, status: 'DRAFT',
  course: { title: 'Basis Data', code: 'IF2230' },
  validation: { passed: true, issues: [] },
  weeks: [
    { week_number: 1, title: 'Model data', learning_outcomes: ['SUB-1'], objectives: ['Membuat ERD'], topics: ['Entitas dan relasi'], teaching_methods: ['Diskusi'], planned_activities: ['learning_material', 'learning_resource'], week_type: 'regular' },
    { week_number: 8, title: 'Ujian Tengah Semester', learning_outcomes: [], objectives: [], topics: [], teaching_methods: [], planned_activities: ['quiz'], week_type: 'uts' },
    { week_number: 16, title: 'Ujian Akhir Semester', week_type: 'uas' },
  ],
  ...overrides,
});
const workflowAt = (stage, status = 'RUNNING') => ({ id: 'wf-1', status, stage, rps_id: 'rps-1', updated_at: `2026-11-07T08:00:0${stage ? stage.length % 10 : 0}Z` });
const event = (name, stage, message = '') => ({ event: name, stage, message, timestamp: '2026-11-07T08:00:00Z' });

let node;
let root;
beforeEach(() => {
  vi.resetAllMocks();
  monitors.byId = {};
  context.course = { id: 'course-1', fullname: 'Basis Data', shortname: 'IF2230', rps_id: 'rps-1' };
  context.workflowId = 'wf-1';
  context.workflow = workflowAt('instructor_review');
  context.events = [];
  plans.listWorkflowPlanVersions.mockResolvedValue([]);
  rpsApi.getRps.mockResolvedValue({ id: 'rps-1', status: 'ANALYZED', workflow_id: 'wf-1', filename: 'rps.pdf' });
  node = document.createElement('div');
  document.body.appendChild(node);
});
afterEach(async () => {
  await act(async () => root?.unmount());
  root = null;
  node.remove();
});

const settle = (ms = 0) => act(() => new Promise((resolve) => setTimeout(resolve, ms)));
async function renderPlan(entry = '/course/2/ai/plan') {
  root ??= createRoot(node);
  await act(async () => root.render(<MemoryRouter initialEntries={[entry]}><CoursePlanPage /></MemoryRouter>));
  await settle();
}
const button = (text) => [...node.querySelectorAll('button')].find((b) => !b.closest('dialog') && b.textContent.trim() === text);
const progressStep = (label) => [...node.querySelectorAll('[aria-label="Progres penyusunan rencana"] li')].find((li) => li.textContent.includes(label));

describe('FE-12.1 status course planning dari event workflow', () => {
  it('menurunkan PLANNING_COURSE, VALIDATING, dan RETRYING khusus tahap course plan', () => {
    expect(coursePlanProgressOf(workflowAt('course_planning'))).toBe('PLANNING_COURSE');
    expect(coursePlanProgressOf(workflowAt('validation'))).toBe('VALIDATING');
    expect(coursePlanProgressOf(workflowAt('retrying'), [event('WORKFLOW_RETRY', 'course_planning')])).toBe('RETRYING');
    // Percobaan ulang analisis RPS bukan progres course planning.
    expect(coursePlanProgressOf(workflowAt('retrying'), [event('WORKFLOW_RETRY', 'rps_analysis')])).toBeNull();
    expect(coursePlanProgressOf(workflowAt('instructor_review'))).toBeNull();
  });

  it('event WORKFLOW_WAITING_FOR_REVIEW memindahkan workflow ke review dan WORKFLOW_FAILED pada tahap rencana dikenali', () => {
    const running = { ...workflowAt('validation'), updated_at: '2026-11-07T07:00:00Z' };
    expect(applyWorkflowEvent(running, event('WORKFLOW_WAITING_FOR_REVIEW', 'instructor_review'))).toMatchObject({ status: 'RUNNING', stage: 'instructor_review' });
    expect(applyWorkflowEvent(running, event('WORKFLOW_PLAN_GENERATED', 'validation')).updated_at).toBe('2026-11-07T08:00:00Z');
    const failed = workflowAt(null, 'FAILED');
    expect(coursePlanFailureOf(failed, [event('WORKFLOW_FAILED', 'course_planning', 'Model tidak merespons.')]).message).toBe('Model tidak merespons.');
    expect(coursePlanFailureOf(failed, [event('WORKFLOW_FAILED', 'rps_analysis', 'x')])).toBeNull();
  });
});

describe('FE-12.1 halaman Rencana', () => {
  it('menampilkan progres per tahap: validasi berjalan setelah penyusunan selesai', async () => {
    context.workflow = workflowAt('validation');
    plans.getWorkflowPlan.mockResolvedValue(null);
    await renderPlan();
    expect(node.textContent).toContain('Agent sedang memvalidasi rencana');
    expect(progressStep('Menyusun rencana').textContent).toContain('Selesai');
    expect(progressStep('Memvalidasi rencana').getAttribute('aria-current')).toBe('step');
    expect(button('Generate rencana')).toBeUndefined();
  });

  it('RETRYING menandai tahap yang sedang dicoba ulang', async () => {
    context.workflow = workflowAt('retrying');
    context.events = [event('WORKFLOW_RETRY', 'validation', 'Mencoba ulang validasi.')];
    plans.getWorkflowPlan.mockResolvedValue(null);
    await renderPlan();
    expect(node.textContent).toContain('Agent sedang mencoba ulang');
    expect(progressStep('Memvalidasi rencana').textContent).toContain('Mencoba ulang');
  });

  it('rencana tampil otomatis setelah workflow selesai menyusun dan menunggu review, tanpa memuat ulang', async () => {
    context.workflow = workflowAt('course_planning');
    plans.getWorkflowPlan.mockResolvedValue(null);
    await renderPlan();
    expect(node.textContent).toContain('Agent sedang menyusun rencana');

    // Event real-time (FE-10.2) memperbarui workflow di layout; halaman memuat GET /workflows/{id}/plan lagi.
    plans.getWorkflowPlan.mockResolvedValue(plan());
    context.workflow = { ...workflowAt('instructor_review'), updated_at: '2026-11-07T08:05:00Z' };
    await renderPlan();
    await settle(350);
    expect(node.textContent).toContain('Rencana course · versi 1');
    expect(node.textContent).toContain('Model data');
    expect(node.querySelector('[aria-label="Progres penyusunan rencana"]')).toBeNull();
    expect(button('Setujui rencana').disabled).toBe(false);
  });

  it('per minggu menampilkan Sub-CPMK, tujuan, topik, metode, rencana aktivitas, dan penanda UTS/UAS', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan());
    await renderPlan();
    const headers = [...node.querySelectorAll('thead th')].map((th) => th.textContent);
    expect(headers).toEqual(['Minggu', 'Topik', 'Sub-CPMK', 'Tujuan pembelajaran', 'Metode mengajar', 'Rencana aktivitas']);
    const rows = node.querySelectorAll('tbody tr');
    for (const text of ['Model data', 'SUB-1', 'Membuat ERD', 'Entitas dan relasi', 'Diskusi', 'Materi', 'Sumber belajar']) expect(rows[0].textContent).toContain(text);
    expect(rows[1].querySelector('th').textContent).toContain('UTS');
    expect(rows[2].querySelector('th').textContent).toContain('UAS');
    expect(rows[0].querySelector('th').textContent).toBe('1');
  });

  it('hasil validasi menampilkan temuan tingkat rencana dan per minggu, dan rencana tidak dapat disetujui', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan({ validation: { passed: false, issues: [
      { code: 'WEEK_TYPE', week: 8, message: 'Minggu 8 harus UTS sesuai RPS.' },
      { code: 'COVERAGE', week: null, message: 'Sub-CPMK SUB-4 belum dicakup.' },
    ] } }));
    await renderPlan();
    const findings = node.querySelector('[aria-label="Temuan validasi"]');
    expect(node.textContent).toContain('Rencana belum lolos validasi');
    expect(findings.textContent).toContain('Sub-CPMK SUB-4 belum dicakup.');
    expect(findings.textContent).toContain('Minggu 8:Minggu 8 harus UTS sesuai RPS.');
    expect(node.querySelectorAll('tbody tr')[1].querySelector('[aria-label="Temuan validasi minggu ini"]').textContent).toContain('Minggu 8 harus UTS sesuai RPS.');
    expect(button('Setujui rencana').disabled).toBe(true);
  });

  it('rencana yang lolos validasi menampilkan keterangan lolos', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan());
    await renderPlan();
    expect(node.textContent).toContain('Lolos validasi');
  });

  it('status FAILED menampilkan pesan kegagalan dan Generate ulang memanggil POST /workflows/{id}/plan', async () => {
    context.workflow = workflowAt(null, 'FAILED');
    context.events = [event('WORKFLOW_FAILED', 'course_planning', 'Agent gagal menyusun rencana setelah 3 percobaan.')];
    plans.getWorkflowPlan.mockResolvedValue(null);
    plans.generateWorkflowPlan.mockResolvedValue({ workflow_id: 'wf-1', status: 'RUNNING' });
    await renderPlan();
    const alert = node.querySelector('[role="alert"]');
    expect(alert.textContent).toContain('Penyusunan rencana gagal');
    expect(alert.textContent).toContain('Agent gagal menyusun rencana setelah 3 percobaan.');
    await act(async () => button('Generate ulang').click());
    expect(plans.generateWorkflowPlan).toHaveBeenCalledWith('wf-1');
    expect(context.refresh).toHaveBeenCalled();
  });

  it('generate yang ditolak backend menampilkan pesannya dan dapat dicoba lagi', async () => {
    context.workflow = workflowAt('instructor_review');
    plans.getWorkflowPlan.mockResolvedValue(null);
    plans.generateWorkflowPlan
      .mockRejectedValueOnce(new ApiError(503, 'INTERNAL_ERROR', 'Layanan sedang tidak dapat diakses.'))
      .mockResolvedValueOnce({ workflow_id: 'wf-1', status: 'RUNNING' });
    await renderPlan();
    await act(async () => button('Generate rencana').click());
    expect(node.querySelector('[role="alert"]').textContent).toContain('Layanan sedang tidak dapat diakses.');
    expect(button('Generate rencana').disabled).toBe(false);
    await act(async () => button('Generate rencana').click());
    expect(plans.generateWorkflowPlan).toHaveBeenCalledTimes(2);
  });

  it('kegagalan regenerasi pada versi yang ditolak menawarkan Generate ulang lewat regenerasi', async () => {
    context.workflow = workflowAt(null, 'FAILED');
    context.events = [event('WORKFLOW_STAGE_STARTED', 'course_planning'), event('WORKFLOW_STAGE_STARTED', 'validation'), event('WORKFLOW_FAILED', 'validation', 'Validasi rencana gagal.')];
    plans.getWorkflowPlan.mockResolvedValue(plan({ status: 'REJECTED' }));
    await renderPlan();
    expect(node.textContent).toContain('Validasi rencana gagal.');
    expect(button('Generate ulang')).toBeDefined();
  });

  it('?workflow= memuat course plan workflow itu dan memantaunya sendiri', async () => {
    monitors.byId['wf-9'] = { workflow: { ...workflowAt('course_planning'), id: 'wf-9' }, events: [] };
    plans.getWorkflowPlan.mockResolvedValue(null);
    await renderPlan('/course/2/ai/plan?workflow=wf-9');
    expect(plans.getWorkflowPlan).toHaveBeenCalledWith('wf-9');
    expect(node.textContent).toContain('Agent sedang menyusun rencana');
  });
});

function PlanProbe() {
  const location = useLocation();
  return <p>PLAN:{location.pathname}{location.search}</p>;
}

async function renderRps() {
  root ??= createRoot(node);
  await act(async () => root.render(
    <MemoryRouter initialEntries={['/course/2/ai/rps']}>
      <Routes>
        <Route path="/course/2/ai/rps" element={<CourseRpsPage />} />
        <Route path="/course/2/ai/plan" element={<PlanProbe />} />
      </Routes>
    </MemoryRouter>,
  ));
  await settle();
  await settle();
}

describe('FE-12.1 tombol Lanjut ke Course Planning pada Hasil Analisis RPS', () => {
  beforeEach(() => {
    rpsApi.getRpsAnalysis.mockResolvedValue({ rps_id: 'rps-1', analyzed_at: '2026-11-07T08:00:00Z', data: sampleRpsStructuredData() });
  });

  it('memanggil POST /workflows/{id}/plan lalu membuka tab Rencana', async () => {
    plans.getWorkflowPlan.mockResolvedValue(null);
    plans.generateWorkflowPlan.mockResolvedValue({ workflow_id: 'wf-1', status: 'RUNNING' });
    await renderRps();
    expect(button('Lanjut ke Course Planning').disabled).toBe(false);
    await act(async () => button('Lanjut ke Course Planning').click());
    expect(plans.generateWorkflowPlan).toHaveBeenCalledWith('wf-1');
    expect(node.textContent).toContain('PLAN:/course/2/ai/plan');
  });

  it('workflow RPS selain workflow project diteruskan lewat ?workflow=', async () => {
    rpsApi.getRps.mockResolvedValue({ id: 'rps-2', status: 'ANALYZED', workflow_id: 'wf-2', filename: 'rps-baru.pdf' });
    plans.getWorkflowPlan.mockResolvedValue(null);
    plans.generateWorkflowPlan.mockResolvedValue({ workflow_id: 'wf-2', status: 'RUNNING' });
    await renderRps();
    await act(async () => button('Lanjut ke Course Planning').click());
    expect(plans.generateWorkflowPlan).toHaveBeenCalledWith('wf-2');
    expect(node.textContent).toContain('PLAN:/course/2/ai/plan?workflow=wf-2');
  });

  it('kegagalan memulai menampilkan pesan yang jelas dan tombol tetap dapat dicoba lagi', async () => {
    plans.getWorkflowPlan.mockResolvedValue(null);
    plans.generateWorkflowPlan.mockRejectedValue(new ApiError(503, 'INTERNAL_ERROR', 'Layanan sedang tidak dapat diakses.'));
    await renderRps();
    await act(async () => button('Lanjut ke Course Planning').click());
    expect(node.querySelector('[role="alert"]').textContent).toContain('Layanan sedang tidak dapat diakses.');
    expect(button('Lanjut ke Course Planning').disabled).toBe(false);
    expect(node.textContent).not.toContain('PLAN:');
  });

  it('409 (rencana sudah ada atau sedang disusun) langsung membuka tab Rencana', async () => {
    plans.getWorkflowPlan.mockResolvedValue(null);
    plans.generateWorkflowPlan.mockRejectedValue(new ApiError(409, 'INVALID_REQUEST', 'Workflow sudah memiliki course plan.'));
    await renderRps();
    await act(async () => button('Lanjut ke Course Planning').click());
    expect(node.textContent).toContain('PLAN:/course/2/ai/plan');
  });

  it('workflow yang sudah punya course plan menampilkan tautan Lihat Course Plan', async () => {
    plans.getWorkflowPlan.mockResolvedValue(plan());
    await renderRps();
    const link = [...node.querySelectorAll('a')].find((a) => a.textContent === 'Lihat Course Plan');
    expect(link.getAttribute('href')).toBe('/course/2/ai/plan');
    expect(button('Lanjut ke Course Planning')).toBeUndefined();
  });

  it('RPS yang belum dianalisis: tombol nonaktif dengan alasannya', async () => {
    rpsApi.getRps.mockResolvedValue({ id: 'rps-1', status: 'PROCESSED', workflow_id: 'wf-1', filename: 'rps.pdf', has_source_document: true });
    await renderRps();
    expect(button('Lanjut ke Course Planning').disabled).toBe(true);
    expect(node.querySelector('#planning-hint').textContent).toBe('Tersedia setelah RPS selesai dianalisis.');
    expect(plans.getWorkflowPlan).not.toHaveBeenCalled();
  });

  it('menghapus tombol Pantau workflow & Kembali ke daftar RPS dan menyediakan tombol Analisis ulang', async () => {
    plans.getWorkflowPlan.mockResolvedValue(null);
    rpsApi.reanalyzeRps.mockResolvedValue({ rps_id: 'rps-1', workflow_id: 'wf-1', status: 'ANALYZING' });
    await renderRps();

    expect(node.textContent).not.toContain('Pantau workflow');
    expect(node.textContent).not.toContain('Kembali ke daftar RPS');

    const reanalyzeBtn = button('Analisis ulang');
    expect(reanalyzeBtn).toBeDefined();
    expect(reanalyzeBtn.disabled).toBe(false);

    rpsApi.getRps.mockResolvedValue({ id: 'rps-1', status: 'ANALYZING', workflow_id: 'wf-1', filename: 'rps.pdf', has_source_document: true });
    await act(async () => reanalyzeBtn.click());
    await settle();

    expect(rpsApi.reanalyzeRps).toHaveBeenCalledWith('rps-1');
    expect(context.refresh).toHaveBeenCalled();
    expect(node.textContent).toContain('Pemrosesan RPS sedang berlangsung');
  });
});
