// Adapted from Rakha accbc21: validated demo credentials and provider-owned token.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setToken, ApiError } from '../src/services/apiClient';
import * as auth from '../src/services/authService';
import * as rps from '../src/services/rpsService';
import * as courses from '../src/services/courseService';
import * as profile from '../src/services/profileService';
import { subscribeCourseEvents } from '../src/services/monitoringSocket';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';

const flush = () => vi.runAllTimersAsync();

beforeEach(async () => {
  vi.useFakeTimers();
  configureMock({ latencyMs: 0, stepMs: 10 });
  resetMockDb();
  localStorage.clear();
  setToken((await auth.login('dosen', 'dosen123')).access_token);
});

afterEach(() => {
  auth.logout();
  resetMockDb();
  vi.useRealTimers();
});

async function expectApiError(promise, status, code) {
  const err = await promise.catch((e) => e);
  expect(err).toBeInstanceOf(ApiError);
  expect(err.status).toBe(status);
  expect(err.code).toBe(code);
}

describe('auth', () => {
  it('mengembalikan user setelah login', async () => {
    const me = await auth.getCurrentUser();
    expect(me).toMatchObject({ name: 'Muchammad Chandra Cahyo Utomo, S. Kom., M. Kom.', role: 'instructor' });
  });

  it('menolak password salah dengan format error standar', async () => {
    await expectApiError(auth.login('dosen', 'salah'), 401, 'AUTHENTICATION_FAILED');
  });

  it('mewajibkan token', async () => {
    auth.logout();
    await expectApiError(courses.listCourses(), 401, 'AUTHENTICATION_FAILED');
  });

  it('menolak mahasiswa untuk operasi dosen (authorization matrix)', async () => {
    setToken((await auth.login('mahasiswa', 'mahasiswa123')).access_token);
    expect((await auth.getCurrentUser()).role).toBe('student');
    await expectApiError(courses.listCourses(), 403, 'AUTHORIZATION_DENIED');
  });
});

describe('RPS', () => {
  it('upload, proses async, lalu analisis tersedia', async () => {
    const file = new File(['%PDF'], 'rps-basis-data.pdf', { type: 'application/pdf' });
    const uploaded = await rps.uploadRps(file);
    expect(uploaded.status).toBe('uploaded');

    const proc = await rps.processRps(uploaded.id);
    expect(proc).toMatchObject({ status: 'processing', agent_run_id: expect.any(String) });
    await expectApiError(rps.getRpsAnalysis(uploaded.id), 409, 'INVALID_REQUEST');

    await flush();
    expect((await rps.getRps(uploaded.id)).status).toBe('processed');
    const analysis = await rps.getRpsAnalysis(uploaded.id);
    expect(analysis.weekly_plan).toHaveLength(16);
  });

  it('menolak file selain PDF/DOCX', async () => {
    const file = new File(['x'], 'rps.txt', { type: 'text/plain' });
    await expectApiError(rps.uploadRps(file), 400, 'INVALID_FILE');
  });
});

describe('profil dosen', () => {
  it('menyimpan perubahan', async () => {
    const saved = await profile.updateProfile({ teaching_style: 'Project based' });
    expect(saved.teaching_style).toBe('Project based');
    expect((await profile.getProfile()).teaching_style).toBe('Project based');
  });
});

describe('workflow course end-to-end', () => {
  it('CREATED → plan → konten → review → Moodle → COMPLETED', async () => {
    const { id } = await courses.createCourse({
      rps_id: 'rps_001',
      moodle_course_id: 'IF2105-C',
      additional_prompt: 'Contoh kasus kampus',
      activity_configuration: { learning_material: true, assignment: true, quiz: true },
    });
    const events = [];
    const unsubscribe = subscribeCourseEvents(id, (ev) => events.push(ev.event));
    const status = async () => (await courses.getCourse(id)).status;
    expect(await status()).toBe('CREATED');

    // Konten tidak boleh digenerate sebelum rencana disetujui.
    await expectApiError(courses.generateContent(id), 409, 'INVALID_REQUEST');

    await courses.generatePlan(id);
    expect(await status()).toBe('PLANNING');
    await flush();
    expect(await status()).toBe('WAITING_PLAN_REVIEW');
    expect((await courses.getPlan(id)).weeks).toHaveLength(16);

    await courses.regeneratePlan(id, 'Perbaiki minggu 5-8');
    await flush();
    const plan = await courses.getPlan(id);
    expect(plan.version).toBe(2);
    expect(plan.weeks[4].note).toContain('Perbaiki minggu 5-8');

    await courses.approvePlan(id);
    expect(await status()).toBe('PLAN_APPROVED');

    await courses.generateContent(id, 'all');
    expect(await status()).toBe('GENERATING_CONTENT');
    await flush();
    expect(await status()).toBe('WAITING_CONTENT_REVIEW');
    const content = await courses.getContent(id);
    expect(content.weeks).toHaveLength(16);
    expect((await courses.getContent(id, 3)).weeks).toHaveLength(1);

    // Validasi awal menemukan masalah di minggu 5; regenerasi memperbaikinya.
    const validation = await courses.getValidation(id);
    expect(validation.result).toBe('failed');
    expect(validation.issues[0]).toMatchObject({ week: 5, severity: 'medium' });

    await courses.regenerateContent(id, 'content_w05', 'Tambahkan Fetch API');
    await flush();
    expect((await courses.getContent(id, 5)).weeks[0].revision).toBe(1);
    expect((await courses.getValidation(id)).result).toBe('passed');

    await courses.rejectContent(id, 'Perlu contoh tambahan');
    expect(await status()).toBe('CONTENT_REJECTED');
    await courses.generateContent(id, [2]);
    await flush();
    expect(await status()).toBe('WAITING_CONTENT_REVIEW');

    // Eksekusi Moodle butuh approval.
    await expectApiError(courses.executeCourse(id), 409, 'REVIEW_REQUIRED');
    await courses.approveContent(id);
    expect(await status()).toBe('APPROVED');

    const { execution_id } = await courses.executeCourse(id);
    await flush();
    const execution = await courses.getExecution(id, execution_id);
    expect(execution.status).toBe('completed');
    expect(execution.completed_items).toBe(execution.total_items);
    expect(await status()).toBe('EXECUTED');

    const { verification_id } = await courses.startVerification(id);
    await flush();
    const verification = await courses.getVerification(id, verification_id);
    expect(verification.result).toBe('passed');
    expect(verification.checks.length).toBeGreaterThan(0);
    expect(await status()).toBe('COMPLETED');

    const runs = (await courses.getAgentRuns(id)).runs;
    expect(runs.every((r) => r.status === 'completed')).toBe(true);
    const monitoring = await courses.getMonitoring(id);
    expect(monitoring.status).toBe('COMPLETED');

    expect(events).toEqual(
      expect.arrayContaining(['PLANNING_COMPLETED', 'CONTENT_GENERATION_COMPLETED', 'EXECUTION_COMPLETED', 'VERIFICATION_COMPLETED']),
    );
    unsubscribe();
  });

  it('eksekusi dapat dibatalkan dan kembali ke APPROVED', async () => {
    const { id } = await courses.createCourse({ rps_id: 'rps_001' });
    await courses.generatePlan(id);
    await flush();
    await courses.approvePlan(id);
    await courses.generateContent(id);
    await flush();
    await courses.approveContent(id);

    const { execution_id } = await courses.executeCourse(id);
    const cancelled = await courses.cancelExecution(id, execution_id);
    expect(cancelled.status).toBe('cancelled');
    await flush();
    expect((await courses.getExecution(id, execution_id)).status).toBe('cancelled');
    expect((await courses.getCourse(id)).status).toBe('APPROVED');
  });

  it('memvalidasi input', async () => {
    await expectApiError(courses.createCourse({ rps_id: 'rps_999' }), 422, 'INVALID_REQUEST');
    await expectApiError(courses.getCourse('nope'), 404, 'RESOURCE_NOT_FOUND');
    await expectApiError(courses.regeneratePlan('course_project_002', '  '), 422, 'INVALID_REQUEST');
    await expectApiError(courses.generateContent('course_project_002', [0]), 409, 'INVALID_REQUEST');
  });
});
