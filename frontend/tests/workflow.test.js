import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../src/services/apiClient';
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
  await auth.login('dosen', 'dosen123');
});

afterEach(() => {
  vi.useRealTimers();
});

async function expectApiError(promise, status, code) {
  const err = await promise.catch((e) => e);
  expect(err).toBeInstanceOf(ApiError);
  expect(err.status).toBe(status);
  expect(err.code).toBe(code);
}

describe('auth', () => {
  it('mengembalikan user setelah login dengan bentuk GET /auth/me backend', async () => {
    const me = await auth.getCurrentUser();
    expect(me).toEqual({ id: 'user_001', username: 'dosen', firstname: 'Rina', lastname: 'Kartika', email: 'dosen@lecturer.itk.ac.id', role: 'INSTRUCTOR' });
    expect(auth.toUiRole(me.role)).toBe('DOSEN');
    expect(auth.toUiRole('STUDENT')).toBe('MAHASISWA');
    expect(auth.toUiRole('UNKNOWN')).toBeNull();
  });

  it('menolak password salah dengan format error standar', async () => {
    const err = await auth.login('dosen', 'salah').catch((e) => e);
    expect(err).toMatchObject({ status: 401, code: 'AUTHENTICATION_FAILED', message: 'Autentikasi gagal.' });
    await expectApiError(auth.login('tidak-ada', 'tidak-ada123'), 401, 'AUTHENTICATION_FAILED');
  });

  it('menolak field kosong dengan VALIDATION_FAILED seperti schema backend', async () => {
    const err = await auth.login('', '').catch((e) => e);
    expect(err).toMatchObject({ status: 422, code: 'VALIDATION_FAILED', message: 'Data request tidak valid.' });
    expect(err.details.map((d) => d.field)).toEqual(['username', 'password']);
    await expectApiError(auth.login('dosen', 'x'.repeat(73)), 422, 'VALIDATION_FAILED');
    // Spasi saja lolos schema (min_length=1), lalu di-strip backend dan tidak cocok → 401.
    await expectApiError(auth.login('   ', 'dosen123'), 401, 'AUTHENTICATION_FAILED');
  });

  it('menerima akun uji backend lewat username atau email', async () => {
    expect((await auth.login('dosen.demo', 'dosen.demo123')).user).toEqual({ id: 'user_006', role: 'INSTRUCTOR' });
    expect((await auth.login(' 11231023@STUDENT.itk.ac.id ', '11231023123')).user).toEqual({ id: 'user_007', role: 'STUDENT' });
  });

  it('mewajibkan token', async () => {
    auth.logout();
    await expectApiError(courses.listCourses(), 401, 'AUTHENTICATION_FAILED');
  });

  it('menolak mahasiswa untuk operasi dosen (authorization matrix)', async () => {
    await auth.login('mahasiswa', 'mahasiswa123');
    expect((await auth.getCurrentUser()).role).toBe('STUDENT');
    await expectApiError(courses.listCourses(), 403, 'AUTHORIZATION_DENIED');
  });
});

describe('RPS', () => {
  const pdf = (name = 'rps-basis-data.pdf', content = '%PDF') => new File([content], name, { type: 'application/pdf' });

  it('upload, proses async, lalu analisis tersedia (kontrak §6.1–§6.3)', async () => {
    const uploaded = await rps.uploadRps(pdf());
    expect(uploaded).toMatchObject({ filename: 'rps-basis-data.pdf', status: 'UPLOADED', schema_version: '2.0', deduplicated: false });

    const proc = await rps.processRps(uploaded.id);
    expect(proc).toEqual({ rps_id: uploaded.id, status: 'PROCESSING', schema_version: '2.0', reused: false });
    await expectApiError(rps.processRps(uploaded.id), 409, 'INVALID_REQUEST');
    await expectApiError(rps.getRpsAnalysis(uploaded.id), 409, 'INVALID_REQUEST');

    await flush();
    expect(await rps.getRps(uploaded.id)).toMatchObject({ status: 'PROCESSED', has_source_document: true, processing_error_code: null });
    expect((await rps.getRpsAnalysis(uploaded.id)).weekly_plan).toHaveLength(16);
    expect(await rps.processRps(uploaded.id)).toMatchObject({ status: 'PROCESSED', reused: true });
  });

  it('mendeduplikasi isi yang sama dan menampilkan item daftar dengan workflow_id', async () => {
    const first = await rps.uploadRps(pdf());
    const again = await rps.uploadRps(pdf());
    expect(again).toMatchObject({ id: first.id, deduplicated: true });
    const { items } = await rps.listRps();
    expect(items.filter((item) => item.id === first.id)).toHaveLength(1);
    expect(items.find((item) => item.id === first.id)).toEqual({
      id: first.id,
      filename: 'rps-basis-data.pdf',
      status: 'UPLOADED',
      schema_version: '2.0',
      workflow_id: null,
      has_source_document: false,
      created_at: expect.any(String),
      updated_at: expect.any(String),
    });
  });

  it('menandai pemrosesan yang gagal dengan kode dan pesan error', async () => {
    const uploaded = await rps.uploadRps(pdf('rps-rusak.pdf'));
    await rps.processRps(uploaded.id);
    await flush();
    expect(await rps.getRps(uploaded.id)).toMatchObject({
      status: 'FAILED',
      processing_error_code: 'RPS_PROCESSING_FAILED',
      processing_error_message: expect.any(String),
    });
  });

  it('menolak file tidak valid seperti default backend (hanya PDF, maks. 20 MiB)', async () => {
    await expectApiError(rps.uploadRps(new File(['x'], 'rps.txt', { type: 'text/plain' })), 400, 'INVALID_FILE');
    await expectApiError(rps.uploadRps(new File(['x'], 'rps.docx')), 400, 'INVALID_FILE');
    await expectApiError(rps.uploadRps(pdf('kosong.pdf', '')), 400, 'INVALID_FILE');
    const big = pdf('besar.pdf');
    Object.defineProperty(big, 'size', { value: 20 * 1024 * 1024 + 1 });
    await expectApiError(rps.uploadRps(big), 400, 'INVALID_FILE');
  });

  it('validateRpsFile menolak format dan ukuran yang salah sebelum dikirim', () => {
    expect(rps.validateRpsFile(null)).toBe('Pilih file RPS terlebih dahulu.');
    expect(rps.validateRpsFile(new File(['x'], 'rps.txt'))).toBe('Format file harus PDF atau DOCX.');
    expect(rps.validateRpsFile(new File(['x'], 'RPS'))).toBe('Format file harus PDF atau DOCX.');
    expect(rps.validateRpsFile(new File([''], 'rps.pdf'))).toMatch(/^File kosong/);
    const big = new File(['x'], 'rps.PDF');
    Object.defineProperty(big, 'size', { value: 21 * 1024 * 1024 });
    expect(rps.validateRpsFile(big)).toBe('Ukuran file 21.0 MB melebihi batas 20.0 MB.');
    expect(rps.validateRpsFile(new File(['x'], 'rps.pdf'))).toBeNull();
    expect(rps.validateRpsFile(new File(['x'], 'RPS Final.DOCX'))).toBeNull();
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
    const generatedPlan = await courses.getPlan(id);
    expect(generatedPlan.weeks).toHaveLength(16);
    expect(generatedPlan.course).toMatchObject({ code: 'IF2105', credits: 3 });
    expect(generatedPlan.weeks[0]).toMatchObject({ week_number: 1, learning_outcomes: ['CPMK-1'], teaching_methods: ['Ceramah', 'diskusi', 'praktikum'] });

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
