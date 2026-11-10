import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ContentGenerationMatrix from '../src/components/ai/course/ContentGenerationMatrix';
import CourseContentPage from '../src/pages/dosen/ai/CourseContentPage';
import * as contentService from '../src/services/contentService';
import * as coursePlanService from '../src/services/coursePlanService';
import {
  AWAITED_ACTION,
  CONTENT_CELL_STATUS,
  WORKFLOW_EVENT,
  awaitedActionOf,
  deriveContentMatrixRows,
  latestContentGenerationRunEvents,
  parseContentEventMessage,
} from '../src/utils/workflowStatus';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockUseCourse = vi.fn();
vi.mock('../src/hooks/useCourse', () => ({
  useCourse: () => mockUseCourse(),
}));

const samplePlan = () => ({
  id: 'plan-1',
  workflow_id: 'wf-1',
  version: 1,
  status: 'APPROVED',
  course: { title: 'Sistem Basis Data', code: 'IF201413' },
  weeks: [
    { week_number: 1, title: 'Konsep Basis Data', week_type: 'regular' },
    { week_number: 2, title: 'Entity Relationship Diagram', week_type: 'regular' },
    { week_number: 3, title: 'Kuis Pemodelan', week_type: 'kuis' },
    { week_number: 8, title: 'UTS', week_type: 'uts' },
  ],
});

const ev = (event, stage, message, timestamp = '2026-11-10T10:01:00Z') => ({
  event,
  workflow_id: 'wf-1',
  stage,
  message,
  timestamp,
});

describe('FE-16.2 utilitas parser event dan matriks konten', () => {
  it('mem-parse event AKTIVITAS_AGENT, RETRY_FIX, dan event akhir BE-19.3 dengan akurat', () => {
    expect(parseContentEventMessage(
      ev(WORKFLOW_EVENT.STAGE_PROGRESS, 'content_generation', 'Minggu 1 - Learning Material dimulai.'),
    )).toEqual({ weekNumber: 1, kind: 'LEARNING_MATERIAL', status: CONTENT_CELL_STATUS.PROCESSING });

    expect(parseContentEventMessage(
      ev(WORKFLOW_EVENT.STAGE_PROGRESS, 'content_generation', 'Minggu 2 - Assignment sedang dihasilkan.'),
    )).toEqual({ weekNumber: 2, kind: 'ASSIGNMENT', status: CONTENT_CELL_STATUS.PROCESSING });

    expect(parseContentEventMessage(
      ev(WORKFLOW_EVENT.RETRY, 'content_generation', 'Minggu 1 - Learning Resource diperbaiki.'),
    )).toEqual({ weekNumber: 1, kind: 'RESOURCE', status: CONTENT_CELL_STATUS.RETRYING });

    expect(parseContentEventMessage(
      ev(WORKFLOW_EVENT.CONTENT_VALIDATED, 'validation', 'Minggu 1 - Learning Material selesai.'),
    )).toEqual({ weekNumber: 1, kind: 'LEARNING_MATERIAL', status: CONTENT_CELL_STATUS.COMPLETED });

    expect(parseContentEventMessage(
      ev(WORKFLOW_EVENT.CONTENT_VALIDATION_FAILED, 'validation', 'Minggu 1 - Learning Resource gagal validasi.'),
    )).toEqual({ weekNumber: 1, kind: 'RESOURCE', status: CONTENT_CELL_STATUS.FAILED });

    expect(parseContentEventMessage(
      ev(WORKFLOW_EVENT.CONTENT_FAILED, 'validation', 'Minggu 3 - Quiz gagal.'),
    )).toEqual({ weekNumber: 3, kind: 'QUIZ', status: CONTENT_CELL_STATUS.FAILED });

    expect(parseContentEventMessage(
      ev(WORKFLOW_EVENT.WEEK_COMPLETED, 'validation', 'Minggu 1 selesai: 1 konten berhasil divalidasi, 1 gagal.'),
    )).toEqual({ weekNumber: 1, weekCompleted: true });
  });

  it('mengambil slice event dari run content_generation terbaru agar event run lama diabaikan', () => {
    const events = [
      ev(WORKFLOW_EVENT.STAGE_STARTED, 'content_generation', 'Mulai run 1', '2026-11-10T09:00:00Z'),
      ev(WORKFLOW_EVENT.CONTENT_FAILED, 'validation', 'Minggu 1 - Learning Material gagal.', '2026-11-10T09:01:00Z'),
      ev(WORKFLOW_EVENT.STAGE_STARTED, 'content_generation', 'Mulai run 2', '2026-11-10T10:00:00Z'),
      ev(WORKFLOW_EVENT.STAGE_PROGRESS, 'content_generation', 'Minggu 1 - Learning Material sedang dihasilkan.', '2026-11-10T10:00:30Z'),
    ];
    const { runEvents, runStartTime } = latestContentGenerationRunEvents(events);
    expect(runEvents).toHaveLength(2);
    expect(runStartTime).toBe(Date.parse('2026-11-10T10:00:00Z'));

    const rows = deriveContentMatrixRows(
      samplePlan(),
      [{ id: 'c1', week_number: 1, kind: 'LEARNING_MATERIAL', version: 1, validation: { status: 'FAILED' }, updated_at: '2026-11-10T09:01:00Z' }],
      events,
      { status: 'RUNNING', stage: 'content_generation' },
    );
    expect(rows[0].cells.LEARNING_MATERIAL.status).toBe(CONTENT_CELL_STATUS.PROCESSING);
  });

  it('awaitedActionOf mengembalikan REVIEW_CONTENT setelah tahap content_generation selesai', () => {
    const wfReview = { status: 'RUNNING', stage: 'instructor_review' };
    const eventsAfterContent = [
      ev(WORKFLOW_EVENT.STAGE_COMPLETED, 'moodle_execution', 'Struktur selesai'),
      ev(WORKFLOW_EVENT.WAITING_FOR_REVIEW, 'instructor_review', 'Menunggu generate konten'),
      ev(WORKFLOW_EVENT.STAGE_STARTED, 'content_generation', 'Generate konten dimulai'),
      ev(WORKFLOW_EVENT.CONTENT_VALIDATED, 'validation', 'Minggu 1 - Learning Material selesai.'),
      ev(WORKFLOW_EVENT.WEEK_COMPLETED, 'validation', 'Minggu 1 selesai: 1 konten berhasil divalidasi, 0 gagal.'),
      ev(WORKFLOW_EVENT.WAITING_FOR_REVIEW, 'instructor_review', 'Menunggu review'),
    ];
    expect(awaitedActionOf(wfReview, eventsAfterContent)).toBe(AWAITED_ACTION.REVIEW_CONTENT);
  });
});

describe('FE-16.2 Matriks Progres & Regenerasi Item', () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);

    mockUseCourse.mockReturnValue({
      course: { name: 'Sistem Basis Data' },
      workflow: { id: 'wf-1', status: 'RUNNING', stage: 'instructor_review' },
      workflowId: 'wf-1',
      events: [],
      refresh: vi.fn(),
    });

    vi.spyOn(coursePlanService, 'getWorkflowPlan').mockResolvedValue(samplePlan());
    vi.spyOn(contentService, 'listWorkflowContents').mockResolvedValue([]);
    vi.spyOn(contentService, 'getWorkflowContent').mockResolvedValue({
      id: 'c-fail-1',
      kind: 'RESOURCE',
      week_number: 1,
      version: 1,
      validation: {
        status: 'FAILED',
        retry_count: 1,
        errors: { resource_url: ['URL resource tidak valid.'] },
      },
    });
    vi.spyOn(contentService, 'regenerateWorkflowContents').mockResolvedValue({
      workflow_id: 'wf-1',
      status: 'GENERATING_CONTENT',
      scope: 'ITEM',
      message: 'Regenerasi konten dijadwalkan; pantau status workflow dan event untuk hasilnya.',
    });
  });

  afterEach(() => {
    act(() => root?.unmount());
    root = null;
    container.remove();
    vi.restoreAllMocks();
  });

  async function renderPage() {
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={['/course/48/ai/content']}>
          <Routes>
            <Route path="/course/:courseId/ai/content" element={<CourseContentPage />} />
          </Routes>
        </MemoryRouter>,
      );
    });
  }

  async function renderMatrix(props) {
    if (!root) root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={['/course/48/ai/content']}>
          <Routes>
            <Route
              path="/course/:courseId/ai/content"
              element={(
                <ContentGenerationMatrix
                  workflowId="wf-1"
                  plan={samplePlan()}
                  {...props}
                />
              )}
            />
          </Routes>
        </MemoryRouter>,
      );
    });
  }

  async function waitFor(check, label, timeout = 3000) {
    const start = Date.now();
    while (!check()) {
      if (Date.now() - start > timeout) {
        throw new Error(`Timeout: ${label}. Isi: ${container.textContent.slice(0, 500)}`);
      }
      await act(() => new Promise((r) => setTimeout(r, 20)));
    }
  }

  const findButton = (text) => [...container.querySelectorAll('button')].find((b) => b.textContent.includes(text));

  it('tidak menampilkan matriks saat belum pernah ada konten atau aktivitas generation', async () => {
    await renderPage();
    await waitFor(() => container.textContent.includes('Generate Semua Minggu'), 'Trigger card');
    expect(container.textContent).not.toContain('Progres Generation Konten');
  });

  it('menampilkan matriks awal dari GET .../contents, termasuk UTS/UAS, ringkasan, dan tautan ke Review', async () => {
    mockUseCourse.mockReturnValue({
      course: { name: 'Sistem Basis Data' },
      workflow: { id: 'wf-1', status: 'RUNNING', stage: 'instructor_review' },
      workflowId: 'wf-1',
      events: [
        ev(WORKFLOW_EVENT.CONTENT_VALIDATED, 'validation', 'Minggu 1 - Learning Material selesai.'),
        ev(WORKFLOW_EVENT.WEEK_COMPLETED, 'validation', 'Minggu 1 selesai: 1 konten berhasil divalidasi, 1 gagal.'),
      ],
      refresh: vi.fn(),
    });
    vi.spyOn(contentService, 'listWorkflowContents').mockResolvedValue([
      {
        id: 'c-ok-1',
        kind: 'LEARNING_MATERIAL',
        week_number: 1,
        title: 'Konsep Basis Data',
        version: 1,
        status: 'DRAFT',
        validation: { status: 'PASSED', score: 1, retry_count: 0 },
        updated_at: '2026-11-10T10:01:00Z',
      },
      {
        id: 'c-fail-1',
        kind: 'RESOURCE',
        week_number: 1,
        title: 'Konsep Basis Data - Learning Resource',
        version: 1,
        status: 'DRAFT',
        validation: { status: 'FAILED', score: 0, retry_count: 1 },
        updated_at: '2026-11-10T10:01:05Z',
      },
    ]);

    await renderPage();
    await waitFor(() => container.textContent.includes('Progres Generation Konten'), 'Matriks konten');

    // Ringkasan selesai & gagal
    expect(container.textContent).toContain('1 selesai');
    expect(container.textContent).toContain('1 gagal');

    // Baris UTS ditampilkan sebagai Ujian / Tidak berlaku
    expect(container.textContent).toContain('Minggu 8');
    expect(container.textContent).toContain('Ujian / Tidak berlaku');

    // Sel Selesai tidak punya tombol pratinjau isi konten
    expect(container.textContent).toContain('✓ Selesai');
    expect(container.textContent).toContain('v1');
    expect(container.querySelector('button[aria-label*="Materi pembelajaran"]')).toBeNull();

    // Minggu 2 yang belum selesai menampilkan Menunggu
    expect(container.textContent).toContain('Menunggu');

    // Tautan ke halaman Review tampil saat WAITING_FOR_REVIEW
    const reviewLink = [...container.querySelectorAll('a')].find((a) => a.textContent.includes('Buka Halaman Review'));
    expect(reviewLink).toBeTruthy();
    expect(reviewLink.getAttribute('href')).toBe('/course/48/ai/review');
  });

  it('memperbarui status sel matriks secara real-time saat event AKTIVITAS_AGENT dan RETRY_FIX tiba', async () => {
    const startEvent = ev(WORKFLOW_EVENT.STAGE_STARTED, 'content_generation', 'Mulai generate', '2026-11-10T10:00:00Z');
    await renderMatrix({
      workflow: { id: 'wf-1', status: 'RUNNING', stage: 'content_generation' },
      contents: [],
      events: [startEvent],
    });
    expect(container.textContent).toContain('Menunggu');

    await renderMatrix({
      workflow: { id: 'wf-1', status: 'RUNNING', stage: 'content_generation' },
      contents: [],
      events: [
        startEvent,
        ev(WORKFLOW_EVENT.STAGE_PROGRESS, 'content_generation', 'Minggu 1 - Learning Material sedang dihasilkan.', '2026-11-10T10:00:10Z'),
      ],
    });
    expect(container.textContent).toContain('Diproses');
    expect(container.textContent).toContain('1 diproses');

    await renderMatrix({
      workflow: { id: 'wf-1', status: 'RUNNING', stage: 'retrying' },
      contents: [],
      events: [
        startEvent,
        ev(WORKFLOW_EVENT.STAGE_PROGRESS, 'content_generation', 'Minggu 1 - Learning Material sedang dihasilkan.', '2026-11-10T10:00:10Z'),
        ev(WORKFLOW_EVENT.RETRY, 'content_generation', 'Minggu 1 - Learning Material diperbaiki.', '2026-11-10T10:00:20Z'),
      ],
    });
    expect(container.textContent).toContain('↻ Retry/Fix');

    await renderMatrix({
      workflow: { id: 'wf-1', status: 'RUNNING', stage: 'instructor_review' },
      contents: [],
      events: [
        startEvent,
        ev(WORKFLOW_EVENT.RETRY, 'content_generation', 'Minggu 1 - Learning Material diperbaiki.', '2026-11-10T10:00:20Z'),
        ev(WORKFLOW_EVENT.CONTENT_VALIDATED, 'validation', 'Minggu 1 - Learning Material selesai.', '2026-11-10T10:00:30Z'),
      ],
    });
    expect(container.textContent).toContain('✓ Selesai');
    expect(container.textContent).toContain('1 selesai');
  });

  it('menampilkan detail error item Gagal dan memicu regenerasi ITEM dengan catatan revisi wajib', async () => {
    const onRegenerated = vi.fn();
    await renderMatrix({
      workflow: { id: 'wf-1', status: 'RUNNING', stage: 'instructor_review' },
      contents: [
        {
          id: 'c-fail-1',
          kind: 'RESOURCE',
          week_number: 1,
          title: 'Konsep Basis Data - Learning Resource',
          version: 1,
          status: 'DRAFT',
          validation: { status: 'FAILED', score: 0, retry_count: 1 },
          updated_at: '2026-11-10T10:01:05Z',
        },
      ],
      events: [],
      onRegenerated,
    });

    // Buka detail error
    await act(async () => {
      findButton('Lihat error').click();
    });
    await waitFor(() => container.textContent.includes('URL resource tidak valid.'), 'Isi detail error');
    expect(contentService.getWorkflowContent).toHaveBeenCalledWith('wf-1', 'c-fail-1');

    // Lanjut klik Regenerasi item ini dari modal error
    await act(async () => {
      findButton('Regenerasi item ini').click();
    });
    await waitFor(() => container.textContent.includes('Catatan revisi'), 'Modal regenerasi');

    // Submit kosong harus ditolak di klien
    await act(async () => {
      findButton('Mulai Regenerasi').click();
    });
    expect(container.textContent).toContain('Catatan revisi wajib diisi.');
    expect(contentService.regenerateWorkflowContents).not.toHaveBeenCalled();

    // Isi catatan revisi lalu submit
    const textarea = container.querySelector('textarea');
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(textarea, 'Gunakan URL dokumentasi PostgreSQL resmi.');
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => {
      findButton('Mulai Regenerasi').click();
    });

    expect(contentService.regenerateWorkflowContents).toHaveBeenCalledWith('wf-1', {
      scope: 'ITEM',
      content_id: 'c-fail-1',
      notes: 'Gunakan URL dokumentasi PostgreSQL resmi.',
    });
    expect(onRegenerated).toHaveBeenCalledTimes(1);
    expect(container.textContent).toContain('Regenerasi konten dijadwalkan');
  });

  it('mengunci tombol Regenerasi ketika workflow sedang berjalan', async () => {
    await renderMatrix({
      workflow: { id: 'wf-1', status: 'RUNNING', stage: 'content_generation' },
      contents: [
        {
          id: 'c-fail-1',
          kind: 'RESOURCE',
          week_number: 1,
          version: 1,
          validation: { status: 'FAILED', retry_count: 0 },
          updated_at: '2026-11-10T10:01:05Z',
        },
      ],
      events: [],
    });

    const regenBtn = container.querySelector('button[aria-label*="Regenerasi Minggu 1 Sumber belajar"]');
    expect(regenBtn.disabled).toBe(true);
  });
});
