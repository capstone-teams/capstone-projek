import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CourseContentPage from '../src/pages/dosen/ai/CourseContentPage';
import { ApiError } from '../src/services/apiClient';
import * as contentService from '../src/services/contentService';
import * as coursePlanService from '../src/services/coursePlanService';
import * as courseService from '../src/services/courseService';
import {
  WORKFLOW_EVENT,
  WORKFLOW_EVENT_LABELS,
  contentGenerationProgressOf,
  eventTypeOf,
  isWorkflowBusy,
} from '../src/utils/workflowStatus';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockUseCourse = vi.fn();
vi.mock('../src/hooks/useCourse', () => ({
  useCourse: () => mockUseCourse(),
}));

const samplePlan = (overrides = {}) => ({
  id: 'plan-1',
  workflow_id: 'wf-1',
  version: 2,
  status: 'APPROVED',
  course: { title: 'Sistem Basis Data', code: 'IF201413' },
  weeks: [
    {
      week_number: 1,
      title: 'Konsep Basis Data',
      week_type: 'regular',
      objectives: ['Mahasiswa memahami konsep dasar DBMS dan arsitektur basis data.'],
      topics: ['Definisi Basis Data', 'DBMS vs File System', 'Arsitektur 3-Schema', 'Model Data'],
      planned_activities: ['learning_material', 'learning_resource', 'assignment'],
    },
    {
      week_number: 2,
      title: 'Entity Relationship Diagram',
      week_type: 'regular',
      objectives: ['Mahasiswa mampu memodelkan ERD dari studi kasus.'],
      topics: ['Entitas dan Atribut', 'Kardinalitas Relasi'],
      planned_activities: ['learning_material'],
    },
    {
      week_number: 3,
      title: 'Kuis Pemodelan Data',
      week_type: 'kuis',
      objectives: ['Evaluasi pemahaman ERD dan normalisasi awal.'],
      topics: [],
      planned_activities: ['quiz'],
    },
    { week_number: 8, title: 'Ujian Tengah Semester', week_type: 'uts', objectives: [], topics: [], planned_activities: [] },
    { week_number: 16, title: 'Ujian Akhir Semester', week_type: 'uas', objectives: [], topics: [], planned_activities: [] },
  ],
  ...overrides,
});

describe('FE-16.1 utilitas status & event content generation', () => {
  it('mendaftarkan event konten BE-19.3 dengan label dan kategori yang sesuai', () => {
    expect(WORKFLOW_EVENT_LABELS[WORKFLOW_EVENT.CONTENT_VALIDATED]).toBeTruthy();
    expect(WORKFLOW_EVENT_LABELS[WORKFLOW_EVENT.CONTENT_VALIDATION_FAILED]).toBeTruthy();
    expect(WORKFLOW_EVENT_LABELS[WORKFLOW_EVENT.CONTENT_FAILED]).toBeTruthy();
    expect(WORKFLOW_EVENT_LABELS[WORKFLOW_EVENT.WEEK_COMPLETED]).toBeTruthy();

    expect(eventTypeOf({ event: WORKFLOW_EVENT.CONTENT_VALIDATED })).toBe('AKTIVITAS_AGENT');
    expect(eventTypeOf({ event: WORKFLOW_EVENT.WEEK_COMPLETED })).toBe('AKTIVITAS_AGENT');
    expect(eventTypeOf({ event: WORKFLOW_EVENT.CONTENT_VALIDATION_FAILED })).toBe('ERROR_FAILURE');
    expect(eventTypeOf({ event: WORKFLOW_EVENT.CONTENT_FAILED })).toBe('ERROR_FAILURE');
  });

  it('membedakan state sibuk workflow dan progres content generation', () => {
    expect(isWorkflowBusy({ status: 'QUEUED', stage: null })).toBe(true);
    expect(isWorkflowBusy({ status: 'RUNNING', stage: 'content_generation' })).toBe(true);
    expect(isWorkflowBusy({ status: 'RUNNING', stage: 'instructor_review' })).toBe(false);
    expect(isWorkflowBusy({ status: 'FAILED', stage: null })).toBe(false);

    expect(contentGenerationProgressOf({ status: 'RUNNING', stage: 'content_generation' }, [])).toBe('GENERATING_CONTENT');
    expect(contentGenerationProgressOf(
      { status: 'RUNNING', stage: 'retrying' },
      [{ event: WORKFLOW_EVENT.RETRY, stage: 'content_generation' }],
    )).toBe('RETRYING');
    expect(contentGenerationProgressOf(
      { status: 'RUNNING', stage: 'validation' },
      [{ event: WORKFLOW_EVENT.STAGE_STARTED, stage: 'content_generation' }],
    )).toBe('VALIDATING');
    expect(contentGenerationProgressOf(
      { status: 'RUNNING', stage: 'validation' },
      [{ event: WORKFLOW_EVENT.STAGE_STARTED, stage: 'course_planning' }],
    )).toBeNull();
  });
});

describe('FE-16.1 Content Generation Trigger & Week Selection', () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);

    mockUseCourse.mockReturnValue({
      course: { name: 'Sistem Basis Data', shortname: 'IF201413' },
      workflow: { id: 'wf-1', status: 'RUNNING', stage: 'instructor_review' },
      workflowId: 'wf-1',
      events: [],
      refresh: vi.fn(),
    });

    vi.spyOn(coursePlanService, 'getWorkflowPlan').mockResolvedValue(samplePlan());
    vi.spyOn(contentService, 'listWorkflowContents').mockResolvedValue([]);
    vi.spyOn(contentService, 'generateWorkflowContents').mockResolvedValue({
      workflow_id: 'wf-1',
      status: 'GENERATING_CONTENT',
      message: 'Generation konten dijadwalkan; pantau status workflow dan event untuk hasilnya.',
    });
  });

  afterEach(() => {
    act(() => root?.unmount());
    root = null;
    container.remove();
    vi.restoreAllMocks();
  });

  async function renderPage(initialEntry = '/course/48/ai/content') {
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={[initialEntry]}>
          <Routes>
            <Route path="/course/:courseId/ai/content" element={<CourseContentPage />} />
          </Routes>
        </MemoryRouter>,
      );
    });
  }

  async function waitFor(check, label, timeout = 3000) {
    const start = Date.now();
    while (!check()) {
      if (Date.now() - start > timeout) {
        throw new Error(`Timeout: ${label}. Isi: ${container.textContent.slice(0, 400)}`);
      }
      await act(() => new Promise((r) => setTimeout(r, 20)));
    }
  }

  const findButton = (text) => [...container.querySelectorAll('button')].find((b) => b.textContent.includes(text));

  it('menonaktifkan tombol generate, menyembunyikan checklist, dan menampilkan tautan ke Rencana bila plan belum APPROVED', async () => {
    vi.spyOn(coursePlanService, 'getWorkflowPlan').mockResolvedValue(samplePlan({ status: 'DRAFT' }));

    await renderPage();
    await waitFor(() => container.textContent.includes('Course plan belum disetujui'), 'Alert plan belum disetujui');

    expect(container.querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
    const generateBtn = findButton('Generate Konten');
    expect(generateBtn).toBeTruthy();
    expect(generateBtn.disabled).toBe(true);

    const planLink = [...container.querySelectorAll('a')].find((a) => a.textContent.includes('Buka Tab Rencana'));
    expect(planLink).toBeTruthy();
    expect(planLink.getAttribute('href')).toContain('/plan');
  });

  it('menampilkan pesan jelas dan tombol nonaktif bila course plan belum ada (404/null)', async () => {
    vi.spyOn(coursePlanService, 'getWorkflowPlan').mockResolvedValue(null);

    await renderPage();
    await waitFor(() => container.textContent.includes('Workflow ini belum memiliki course plan'), 'Plan null');

    expect(container.querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
    const generateBtn = findButton('Generate Konten');
    expect(generateBtn.disabled).toBe(true);
  });

  it('langsung menampilkan checklist tercentang semua (tanpa radio) dan memicu generate semua minggu', async () => {
    const refresh = vi.fn();
    mockUseCourse.mockReturnValue({
      course: { name: 'Sistem Basis Data' },
      workflow: { id: 'wf-1', status: 'RUNNING', stage: 'instructor_review' },
      workflowId: 'wf-1',
      events: [],
      refresh,
    });

    await renderPage();
    await waitFor(() => container.textContent.includes('Sistem Basis Data'), 'Checklist plan disetujui');

    // Tidak ada radio button; hanya satu daftar checklist card tanpa scroll box internal
    expect(container.querySelectorAll('input[type="radio"]')).toHaveLength(0);
    const weekList = container.querySelector('ul[aria-label="Daftar minggu course plan"]');
    expect(weekList).toBeTruthy();
    expect(weekList.className).not.toContain('overflow-y-auto');
    expect(container.textContent).toContain('Versi 2');
    expect(container.textContent).toContain('Disetujui');
    expect(container.textContent).toContain('3 dari 3 minggu dipilih · Total 5 minggu (2 minggu ujian dilewati)');

    // Setiap card menampilkan tujuan, topik (maks 3 + sisa), dan rencana aktivitas dari response plan
    expect(container.textContent).toContain('Tujuan: Mahasiswa memahami konsep dasar DBMS dan arsitektur basis data.');
    expect(container.textContent).toContain('Definisi Basis Data');
    expect(container.textContent).toContain('Arsitektur 3-Schema');
    expect(container.textContent).not.toContain('Model Data');
    expect(container.textContent).toContain('+1 topik lainnya');
    expect(container.textContent).toContain('Materi');
    expect(container.textContent).toContain('Sumber belajar');
    expect(container.textContent).toContain('Tugas');
    expect(container.textContent).toContain('Kuis');
    expect(container.textContent).toContain('Minggu ujian · tidak menghasilkan konten pembelajaran.');

    // Seluruh minggu non-ujian tercentang otomatis; UTS & UAS disabled dan tidak tercentang
    const week1Box = container.querySelector('input[type="checkbox"][aria-label*="Minggu 1:"]');
    const week2Box = container.querySelector('input[type="checkbox"][aria-label*="Minggu 2:"]');
    const week3Box = container.querySelector('input[type="checkbox"][aria-label*="Minggu 3:"]');
    const utsBox = container.querySelector('input[type="checkbox"][aria-label*="Minggu 8"]');
    const uasBox = container.querySelector('input[type="checkbox"][aria-label*="Minggu 16"]');

    expect(week1Box.checked).toBe(true);
    expect(week2Box.checked).toBe(true);
    expect(week3Box.checked).toBe(true);
    expect(utsBox.checked).toBe(false);
    expect(utsBox.disabled).toBe(true);
    expect(uasBox.checked).toBe(false);
    expect(uasBox.disabled).toBe(true);

    expect(findButton('Kosongkan pilihan')).toBeTruthy();

    const generateBtn = findButton('Generate Semua Minggu');
    expect(generateBtn.disabled).toBe(false);

    await act(async () => {
      generateBtn.click();
    });

    expect(contentService.generateWorkflowContents).toHaveBeenCalledWith('wf-1', 'all');
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(container.textContent).toContain('Generation konten dijadwalkan');
    // Centang tetap dipertahankan setelah submit
    expect(week1Box.checked).toBe(true);
    expect(week2Box.checked).toBe(true);
  });

  it('mendukung toggle Kosongkan pilihan <-> Pilih semua minggu dan memilih sebagian minggu', async () => {
    await renderPage();
    await waitFor(() => findButton('Kosongkan pilihan'), 'Tombol toggle');

    // Kosongkan semua pilihan
    await act(async () => {
      findButton('Kosongkan pilihan').click();
    });

    const week1Box = container.querySelector('input[type="checkbox"][aria-label*="Minggu 1:"]');
    const week2Box = container.querySelector('input[type="checkbox"][aria-label*="Minggu 2:"]');
    const week3Box = container.querySelector('input[type="checkbox"][aria-label*="Minggu 3:"]');

    expect(week1Box.checked).toBe(false);
    expect(week2Box.checked).toBe(false);
    expect(week3Box.checked).toBe(false);
    expect(findButton('Pilih semua minggu')).toBeTruthy();

    const emptyBtn = findButton('Generate Konten');
    expect(emptyBtn).toBeTruthy();
    expect(emptyBtn.disabled).toBe(true);

    // Pilih Minggu 1 dan Minggu 3 secara manual
    await act(async () => {
      week1Box.click();
      week3Box.click();
    });

    expect(findButton('Pilih semua minggu')).toBeTruthy();
    const partialBtn = findButton('Generate 2 Minggu Terpilih');
    expect(partialBtn).toBeTruthy();
    expect(partialBtn.disabled).toBe(false);

    await act(async () => {
      partialBtn.click();
    });

    expect(contentService.generateWorkflowContents).toHaveBeenCalledWith('wf-1', [1, 3]);
    expect(week1Box.checked).toBe(true);
    expect(week2Box.checked).toBe(false);
    expect(week3Box.checked).toBe(true);

    // Pilih semua minggu kembali (mengecualikan UTS/UAS)
    await act(async () => {
      findButton('Pilih semua minggu').click();
    });

    expect(week2Box.checked).toBe(true);
    expect(container.querySelector('input[type="checkbox"][aria-label*="Minggu 8"]').checked).toBe(false);
    expect(findButton('Kosongkan pilihan')).toBeTruthy();
    expect(findButton('Generate Semua Minggu')).toBeTruthy();
  });

  it('menonaktifkan checklist, tombol toggle, dan tombol generate saat generation konten berjalan', async () => {
    mockUseCourse.mockReturnValue({
      course: { name: 'Sistem Basis Data' },
      workflow: {
        id: 'wf-1',
        status: 'RUNNING',
        stage: 'content_generation',
        progress: { completed: 1, total: 3 },
      },
      workflowId: 'wf-1',
      events: [],
      refresh: vi.fn(),
    });

    await renderPage();
    await waitFor(() => container.textContent.includes('Membuat konten mingguan…'), 'Progress bar generation');

    const progress = container.querySelector('[role="progressbar"]');
    expect(progress).toBeTruthy();
    expect(findButton('Generate Semua Minggu').disabled).toBe(true);
    expect(findButton('Kosongkan pilihan').disabled).toBe(true);
    expect(container.querySelector('input[type="checkbox"][aria-label*="Minggu 1:"]').disabled).toBe(true);
  });

  it('menampilkan pesan error backend bila request generate ditolak (mis. 409/422)', async () => {
    vi.spyOn(contentService, 'generateWorkflowContents').mockRejectedValue(
      new ApiError(409, 'INVALID_REQUEST', 'Tidak ada jenis konten aktif yang dapat dihasilkan pada minggu yang dipilih.'),
    );

    await renderPage();
    await waitFor(() => container.textContent.includes('Generate Semua Minggu'), 'Siap generate');

    await act(async () => {
      findButton('Generate Semua Minggu').click();
    });

    expect(container.querySelector('[role="alert"]').textContent).toContain(
      'Tidak ada jenis konten aktif yang dapat dihasilkan pada minggu yang dipilih.',
    );
  });

  it('tetap mempertahankan fallback ProjectContent untuk mode mock legacy tanpa workflowId', async () => {
    mockUseCourse.mockReturnValue({
      course: { id: 'course_project_1', status: 'PLAN_APPROVED' },
      workflow: null,
      workflowId: null,
      events: [],
      version: 0,
      refresh: vi.fn(),
    });
    vi.spyOn(courseService, 'getContent').mockResolvedValue({ weeks: [] });
    vi.spyOn(courseService, 'getPlan').mockResolvedValue({ weeks: [{ week: 1, topic: 'Pengantar' }] });

    await renderPage();
    await waitFor(() => container.textContent.includes('Generate semua minggu'), 'Legacy ProjectContent');
    expect(courseService.getContent).toHaveBeenCalledWith('course_project_1');
  });
});
