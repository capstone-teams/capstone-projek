/**
 * Mock Backend API yang berjalan di browser.
 *
 * Meniru kontrak di docs/02. design/design-api.md: path, payload, kode error,
 * operasi async (202 + agent run + event WebSocket), dan transisi state workflow (§20).
 * Semua data hanya di memori dan hilang saat halaman di-reload.
 */
import {
  MOCK_INVALID_PASSWORD,
  MOCK_USERS,
  SAMPLE_TOPICS,
  buildPlanWeeks,
  buildRpsAnalysis,
  buildWeekContent,
} from './mockData';

const settings = { latencyMs: 250, stepMs: 600 };

/** Atur kecepatan simulasi (dipakai di test). */
export function configureMock(options) {
  Object.assign(settings, options);
}

const TOTAL_WEEKS = SAMPLE_TOPICS.length;
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

let db;
let seq;
const listeners = new Map();
const timers = new Set();

// ---------------------------------------------------------------- helpers

const now = () => new Date().toISOString();
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function nextId(prefix) {
  seq[prefix] = (seq[prefix] || 0) + 1;
  return `${prefix}_${String(seq[prefix]).padStart(3, '0')}`;
}

const ok = (data, status = 200) => ({ status, data });
const fail = (status, code, message, details = []) => ({ status, data: { error: { code, message, details } } });
const conflict = (message) => fail(409, 'INVALID_REQUEST', message);
const notFound = (what) => fail(404, 'RESOURCE_NOT_FOUND', `${what} tidak ditemukan.`);

function schedule(steps) {
  steps.forEach((step, i) => {
    const t = setTimeout(() => {
      timers.delete(t);
      step();
    }, settings.stepMs * (i + 1));
    timers.add(t);
  });
}

function emit(course, event, extra = {}) {
  const payload = { event, course_id: course.id, timestamp: now(), ...extra };
  course.events.push(payload);
  if (course.events.length > 200) course.events.shift();
  listeners.get(course.id)?.forEach((fn) => fn(payload));
}

function setStatus(course, status, stage = null) {
  course.status = status;
  course.stage = stage;
  course.updated_at = now();
  emit(course, 'STATUS_CHANGED', { status, stage });
}

function createRun(type, course, stage) {
  const run = { id: nextId('run'), type, status: 'running', stage, course_id: course?.id ?? null, started_at: now(), finished_at: null };
  db.runs.push(run);
  return run;
}

function finishRun(run, status = 'completed') {
  run.status = status;
  run.finished_at = now();
}

function publicCourse(c) {
  return {
    id: c.id,
    rps_id: c.rps_id,
    name: c.name,
    code: c.code,
    moodle_course_id: c.moodle_course_id,
    additional_prompt: c.additional_prompt,
    activity_configuration: c.activity_configuration,
    status: c.status,
    stage: c.stage,
    progress: c.progress,
    latest_execution_id: c.latestExecutionId,
    latest_verification_id: c.latestVerificationId,
    created_at: c.created_at,
    updated_at: c.updated_at,
  };
}

function publicRps(r) {
  return { id: r.id, filename: r.filename, size: r.size, status: r.status, created_at: r.created_at };
}

function contentList(course) {
  return Object.values(course.content).sort((a, b) => a.week - b.week);
}

function countItems(week) {
  return 1 + week.materials.length + (week.activities.assignment ? 1 : 0) + (week.activities.quiz ? 1 : 0);
}

// ---------------------------------------------------------------- workflow simulation

function runValidation(course) {
  const issues = [];
  for (let w = 1; w <= TOTAL_WEEKS; w++) {
    const week = course.content[w];
    if (!week) {
      issues.push({ type: 'structure', severity: 'high', week: w, message: `Konten minggu ${w} belum digenerate.` });
    } else if (w === 5 && week.revision === 0) {
      issues.push({
        type: 'rps_adherence',
        severity: 'medium',
        week: 5,
        content_id: week.id,
        message: 'Materi minggu 5 belum mencakup sub-topik Fetch API yang tercantum di RPS.',
      });
    }
  }
  course.validation = {
    validation_id: nextId('validation'),
    status: 'completed',
    result: issues.length ? 'failed' : 'passed',
    issues,
    validated_at: now(),
  };
  return course.validation;
}

function startContentGeneration(course, weeks, { runType = 'content_generation', instruction = null } = {}) {
  const run = createRun(runType, course, `week_${weeks[0]}`);
  course.progress = { completed: 0, total: weeks.length };
  setStatus(course, 'GENERATING_CONTENT', `week_${weeks[0]}`);
  emit(course, 'CONTENT_GENERATION_STARTED', { week: weeks[0], agent_run_id: run.id });

  const steps = weeks.map((w, i) => () => {
    const prev = course.content[w];
    const topic = course.plan?.weeks.find((p) => p.week === w)?.topic ?? SAMPLE_TOPICS[w - 1];
    const content = buildWeekContent(w, topic, course.activity_configuration, prev ? prev.revision + 1 : 0);
    if (instruction) content.last_instruction = instruction;
    course.content[w] = content;
    course.progress.completed = i + 1;
    emit(course, 'CONTENT_GENERATION_COMPLETED', { week: w, progress: { ...course.progress } });

    const next = weeks[i + 1];
    if (next) {
      course.stage = `week_${next}`;
      run.stage = course.stage;
      emit(course, 'CONTENT_GENERATION_STARTED', { week: next, agent_run_id: run.id });
    }
  });

  steps.push(() => {
    finishRun(run);
    const vRun = createRun('validation', course, 'validation');
    setStatus(course, 'VALIDATING', 'validation');
    emit(course, 'VALIDATION_STARTED', { agent_run_id: vRun.id });
    course.pendingValidationRun = vRun;
  });
  steps.push(() => {
    const result = runValidation(course);
    finishRun(course.pendingValidationRun);
    emit(course, 'VALIDATION_COMPLETED', { result: result.result, issue_count: result.issues.length });
    setStatus(course, 'WAITING_CONTENT_REVIEW', 'content_review');
  });

  schedule(steps);
  return run;
}

function startPlanning(course, instruction) {
  const run = createRun('course_planning', course, 'course_planning');
  setStatus(course, 'PLANNING', 'course_planning');
  emit(course, 'PLANNING_STARTED', { agent_run_id: run.id });
  schedule([
    () => {
      course.stage = 'drafting_weeks';
      run.stage = 'drafting_weeks';
      emit(course, 'PLANNING_PROGRESS', { stage: 'drafting_weeks' });
    },
    () => {
      const version = (course.plan?.version ?? 0) + 1;
      course.plan = {
        id: course.plan?.id ?? nextId('plan'),
        course_id: course.id,
        version,
        status: 'draft',
        instruction: instruction ?? null,
        weeks: buildPlanWeeks(instruction),
      };
      finishRun(run);
      emit(course, 'PLANNING_COMPLETED', { version });
      setStatus(course, 'WAITING_PLAN_REVIEW', 'plan_review');
    },
  ]);
  return run;
}

// ---------------------------------------------------------------- handlers

const handlers = {
  login(_p, { body }) {
    if (!body?.username || !body?.password || body.password === MOCK_INVALID_PASSWORD) {
      return fail(401, 'AUTHENTICATION_FAILED', 'Username atau password salah.');
    }
    // Akun dosen Moodle mana pun diterima sebagai instructor.
    let user = MOCK_USERS.find((u) => u.username === body.username);
    if (!user) {
      user = { id: `user_${body.username}`, username: body.username, name: body.username, email: '', role: 'instructor' };
      MOCK_USERS.push(user);
    }
    return ok({ access_token: `mock-token:${user.id}`, token_type: 'bearer', user: { id: user.id, role: user.role } });
  },

  me(_p, { user }) {
    const { id, name, email, role } = user;
    return ok({ id, name, email, role });
  },

  // RPS
  listRps: () => ok({ items: db.rps.map(publicRps).reverse() }),

  uploadRps(_p, { body }) {
    const file = body?.get?.('file');
    if (!file) return fail(400, 'INVALID_FILE', 'File RPS wajib diunggah.');
    if (!/\.(pdf|docx)$/i.test(file.name)) return fail(400, 'INVALID_FILE', 'Format file harus PDF atau DOCX.');
    if (file.size > MAX_UPLOAD_BYTES) return fail(400, 'INVALID_FILE', 'Ukuran file maksimal 10 MB.');
    const rps = { id: nextId('rps'), filename: file.name, size: file.size, status: 'uploaded', created_at: now(), analysis: null };
    db.rps.push(rps);
    return ok({ id: rps.id, filename: rps.filename, status: rps.status }, 201);
  },

  getRps({ rpsId }) {
    const rps = db.rps.find((r) => r.id === rpsId);
    return rps ? ok(publicRps(rps)) : notFound('RPS');
  },

  processRps({ rpsId }) {
    const rps = db.rps.find((r) => r.id === rpsId);
    if (!rps) return notFound('RPS');
    if (!['uploaded', 'failed'].includes(rps.status)) return conflict(`RPS berstatus "${rps.status}" tidak dapat diproses ulang.`);
    const run = createRun('rps_processing', null, 'document_extraction');
    rps.status = 'processing';
    schedule([
      () => {
        rps.status = 'analyzing';
        run.stage = 'rps_analysis';
      },
      () => {
        rps.analysis = buildRpsAnalysis(rps.id);
        rps.status = 'processed';
        finishRun(run);
      },
    ]);
    return ok({ rps_id: rps.id, status: 'processing', agent_run_id: run.id }, 202);
  },

  getRpsAnalysis({ rpsId }) {
    const rps = db.rps.find((r) => r.id === rpsId);
    if (!rps) return notFound('RPS');
    if (!rps.analysis) return conflict('RPS belum selesai diproses.');
    return ok(rps.analysis);
  },

  // Instructor profile
  getProfile: () => ok(db.profile),

  updateProfile(_p, { body }) {
    const fields = ['teaching_style', 'language_preference', 'content_preference'];
    const invalid = fields.filter((f) => body?.[f] != null && typeof body[f] !== 'string');
    if (invalid.length) return fail(422, 'INVALID_REQUEST', 'Field profil harus berupa teks.', invalid);
    fields.forEach((f) => {
      if (body?.[f] != null) db.profile[f] = body[f].trim();
    });
    db.profile.updated_at = now();
    return ok(db.profile);
  },

  // Course
  listCourses: () => ok({ courses: db.courses.map(publicCourse).reverse() }),

  createCourse(_p, { body }) {
    const rps = db.rps.find((r) => r.id === body?.rps_id);
    if (!rps) return fail(422, 'INVALID_REQUEST', 'rps_id tidak valid.', ['rps_id']);
    if (rps.status !== 'processed') return fail(422, 'INVALID_REQUEST', 'RPS harus selesai diproses terlebih dahulu.', ['rps_id']);
    const cfg = body.activity_configuration ?? {};
    const activity_configuration = {
      learning_material: cfg.learning_material !== false,
      assignment: !!cfg.assignment,
      quiz: !!cfg.quiz,
    };
    const course = newCourse({
      rps,
      moodle_course_id: body.moodle_course_id?.trim() || null,
      additional_prompt: body.additional_prompt?.trim() || '',
      activity_configuration,
    });
    emit(course, 'COURSE_CREATED');
    return ok({ id: course.id, status: 'created' }, 201);
  },

  getCourse: (_p, { course }) => ok(publicCourse(course)),

  updateActivityConfiguration(_p, { course, body }) {
    if (['APPROVED', 'EXECUTING', 'EXECUTED', 'VERIFYING', 'COMPLETED'].includes(course.status)) {
      return conflict('Konfigurasi aktivitas tidak dapat diubah setelah konten disetujui.');
    }
    if (body?.learning_material === false && !body?.assignment && !body?.quiz) {
      return fail(422, 'INVALID_REQUEST', 'Minimal satu jenis aktivitas harus aktif.');
    }
    course.activity_configuration = {
      learning_material: !!body.learning_material,
      assignment: !!body.assignment,
      quiz: !!body.quiz,
    };
    course.updated_at = now();
    return ok(course.activity_configuration);
  },

  // Course planning
  generatePlan(_p, { course }) {
    if (course.status !== 'CREATED') return conflict('Course plan hanya dapat dibuat pada status CREATED.');
    const run = startPlanning(course);
    return ok({ course_id: course.id, agent_run_id: run.id, status: 'planning' }, 202);
  },

  getPlan(_p, { course }) {
    return course.plan ? ok(course.plan) : notFound('Course plan');
  },

  approvePlan(_p, { course }) {
    if (course.status !== 'WAITING_PLAN_REVIEW') return conflict('Course plan tidak sedang menunggu review.');
    course.plan.status = 'approved';
    emit(course, 'PLAN_APPROVED');
    setStatus(course, 'PLAN_APPROVED');
    return ok({ course_id: course.id, status: 'approved' });
  },

  regeneratePlan(_p, { course, body }) {
    if (course.status !== 'WAITING_PLAN_REVIEW') return conflict('Course plan hanya dapat diregenerasi saat menunggu review.');
    if (!body?.instruction?.trim()) return fail(422, 'INVALID_REQUEST', 'Instruksi perbaikan wajib diisi.', ['instruction']);
    const run = startPlanning(course, body.instruction.trim());
    return ok({ agent_run_id: run.id, status: 'regenerating' }, 202);
  },

  // Content
  generateContent(_p, { course, body }) {
    if (!['PLAN_APPROVED', 'WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED'].includes(course.status)) {
      return conflict('Konten hanya dapat digenerate setelah course plan disetujui.');
    }
    let weeks = body?.weeks ?? 'all';
    if (weeks === 'all') weeks = Array.from({ length: TOTAL_WEEKS }, (_, i) => i + 1);
    const valid = Array.isArray(weeks) && weeks.length && weeks.every((w) => Number.isInteger(w) && w >= 1 && w <= TOTAL_WEEKS);
    if (!valid) return fail(422, 'INVALID_REQUEST', `weeks harus "all" atau daftar minggu 1-${TOTAL_WEEKS}.`, ['weeks']);
    const run = startContentGeneration(course, [...new Set(weeks)].sort((a, b) => a - b));
    return ok({ agent_run_id: run.id, status: 'generating' }, 202);
  },

  getContent(_p, { course, query }) {
    let weeks = contentList(course);
    if (query?.week != null) weeks = weeks.filter((w) => w.week === Number(query.week));
    return ok({ course_id: course.id, weeks });
  },

  regenerateContent({ contentId }, { course, body }) {
    if (!['WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED'].includes(course.status)) {
      return conflict('Konten hanya dapat diregenerasi saat tahap review.');
    }
    const target = contentList(course).find((c) => c.id === contentId);
    if (!target) return notFound('Konten');
    if (!body?.instruction?.trim()) return fail(422, 'INVALID_REQUEST', 'Instruksi perbaikan wajib diisi.', ['instruction']);
    const run = startContentGeneration(course, [target.week], {
      runType: 'content_regeneration',
      instruction: body.instruction.trim(),
    });
    return ok({ agent_run_id: run.id, status: 'regenerating' }, 202);
  },

  // Validation
  validateContent(_p, { course }) {
    if (!['WAITING_CONTENT_REVIEW', 'CONTENT_REJECTED'].includes(course.status)) {
      return conflict('Validasi hanya dapat dijalankan setelah konten selesai digenerate.');
    }
    const result = runValidation(course);
    emit(course, 'VALIDATION_COMPLETED', { result: result.result, issue_count: result.issues.length });
    return ok(result);
  },

  getValidation(_p, { course }) {
    return course.validation ? ok(course.validation) : notFound('Hasil validasi');
  },

  // Review
  getReview(_p, { course }) {
    const issues = course.validation?.issues ?? [];
    return ok({
      course_id: course.id,
      status: course.status === 'WAITING_CONTENT_REVIEW' ? 'waiting_review' : course.status.toLowerCase(),
      validation_result: course.validation?.result ?? null,
      rejections: course.rejections,
      items: contentList(course).map((c) => ({
        content_id: c.id,
        week: c.week,
        topic: c.topic,
        revision: c.revision,
        material_count: c.materials.length,
        has_assignment: !!c.activities.assignment,
        has_quiz: !!c.activities.quiz,
        issues: issues.filter((i) => i.week === c.week),
      })),
    });
  },

  approveContent(_p, { course }) {
    if (course.status !== 'WAITING_CONTENT_REVIEW') return conflict('Konten tidak sedang menunggu review.');
    const blocking = (course.validation?.issues ?? []).filter((i) => i.severity === 'high');
    if (blocking.length) return fail(422, 'VALIDATION_FAILED', 'Masih ada masalah validasi tingkat high.', blocking);
    emit(course, 'CONTENT_APPROVED');
    setStatus(course, 'APPROVED');
    return ok({ course_id: course.id, status: 'approved' });
  },

  rejectContent(_p, { course, body }) {
    if (course.status !== 'WAITING_CONTENT_REVIEW') return conflict('Konten tidak sedang menunggu review.');
    if (!body?.reason?.trim()) return fail(422, 'INVALID_REQUEST', 'Alasan penolakan wajib diisi.', ['reason']);
    course.rejections.push({ reason: body.reason.trim(), rejected_at: now() });
    emit(course, 'CONTENT_REJECTED', { reason: body.reason.trim() });
    setStatus(course, 'CONTENT_REJECTED');
    return ok({ course_id: course.id, status: 'rejected' });
  },

  // Moodle execution
  executeCourse(_p, { course }) {
    if (course.status !== 'APPROVED') return fail(409, 'REVIEW_REQUIRED', 'Konten harus disetujui sebelum dieksekusi ke Moodle.');
    const weeks = contentList(course);
    const execution = {
      execution_id: nextId('execution'),
      status: 'queued',
      moodle_course_id: course.moodle_course_id,
      completed_items: 0,
      failed_items: 0,
      total_items: weeks.reduce((sum, w) => sum + countItems(w), 0),
      started_at: now(),
      finished_at: null,
    };
    db.executions[execution.execution_id] = execution;
    course.latestExecutionId = execution.execution_id;
    const run = createRun('moodle_execution', course, 'queued');
    course.progress = { completed: 0, total: weeks.length };
    setStatus(course, 'EXECUTING', 'queued');
    emit(course, 'EXECUTION_STARTED', { execution_id: execution.execution_id });

    const active = () => execution.status === 'queued' || execution.status === 'running';
    const steps = weeks.map((w, i) => () => {
      if (!active()) return;
      execution.status = 'running';
      execution.completed_items += countItems(w);
      course.progress.completed = i + 1;
      course.stage = `week_${w.week}`;
      run.stage = course.stage;
      emit(course, 'EXECUTION_PROGRESS', {
        execution_id: execution.execution_id,
        week: w.week,
        completed_items: execution.completed_items,
        total_items: execution.total_items,
      });
    });
    steps.push(() => {
      if (!active()) return;
      execution.status = 'completed';
      execution.finished_at = now();
      finishRun(run);
      emit(course, 'EXECUTION_COMPLETED', { execution_id: execution.execution_id });
      setStatus(course, 'EXECUTED', 'verification_pending');
    });
    schedule(steps);
    return ok({ execution_id: execution.execution_id, status: 'queued' }, 202);
  },

  getExecution({ executionId }) {
    const ex = db.executions[executionId];
    return ex ? ok(ex) : notFound('Eksekusi');
  },

  cancelExecution({ executionId }, { course }) {
    const ex = db.executions[executionId];
    if (!ex) return notFound('Eksekusi');
    if (!['queued', 'running'].includes(ex.status)) return conflict(`Eksekusi berstatus "${ex.status}" tidak dapat dibatalkan.`);
    ex.status = 'cancelled';
    ex.finished_at = now();
    const run = db.runs.findLast((r) => r.course_id === course.id && r.type === 'moodle_execution');
    if (run) finishRun(run, 'cancelled');
    emit(course, 'EXECUTION_CANCELLED', { execution_id: executionId });
    setStatus(course, 'APPROVED');
    return ok(ex);
  },

  // Verification
  startVerification(_p, { course }) {
    if (!['EXECUTED', 'COMPLETED'].includes(course.status)) return conflict('Verifikasi hanya dapat dijalankan setelah eksekusi selesai.');
    const weeks = contentList(course);
    const verification = { verification_id: nextId('verification'), status: 'running', result: null, checks: [], started_at: now() };
    db.verifications[verification.verification_id] = verification;
    course.latestVerificationId = verification.verification_id;
    const run = createRun('verification', course, 'verification');
    setStatus(course, 'VERIFYING', 'verification');
    emit(course, 'VERIFICATION_STARTED', { verification_id: verification.verification_id });

    const count = (pred) => weeks.filter(pred).length;
    const checks = [
      { name: 'course_exists', label: 'Course tersedia di Moodle' },
      { name: 'sections', label: `${weeks.length} section mingguan dibuat` },
      { name: 'materials', label: `${count((w) => w.materials.length)} materi pembelajaran tersedia` },
      { name: 'assignments', label: `${count((w) => w.activities.assignment)} assignment terpasang` },
      { name: 'quizzes', label: `${count((w) => w.activities.quiz)} quiz terpasang` },
      { name: 'student_access', label: 'Mahasiswa dapat mengakses course' },
    ];
    schedule([
      ...checks.map((check) => () => {
        verification.checks.push({ ...check, status: 'passed' });
        emit(course, 'VERIFICATION_CHECK', { check: check.name, status: 'passed' });
      }),
      () => {
        verification.status = 'completed';
        verification.result = 'passed';
        verification.finished_at = now();
        finishRun(run);
        emit(course, 'VERIFICATION_COMPLETED', { result: 'passed' });
        setStatus(course, 'COMPLETED');
      },
    ]);
    return ok({ verification_id: verification.verification_id, status: 'running' }, 202);
  },

  getVerification({ verificationId }) {
    const v = db.verifications[verificationId];
    return v ? ok(v) : notFound('Verifikasi');
  },

  // Agent runs & monitoring
  getAgentRun({ runId }) {
    const run = db.runs.find((r) => r.id === runId);
    return run ? ok(run) : notFound('Agent run');
  },

  getAgentRuns: (_p, { course }) => ok({ runs: db.runs.filter((r) => r.course_id === course.id).reverse() }),

  getMonitoring(_p, { course }) {
    return ok({
      course_id: course.id,
      status: course.status,
      stage: course.stage,
      progress: course.progress,
      recent_events: course.events.slice(-50),
    });
  },
};

// ---------------------------------------------------------------- routing

const ROUTES = [
  ['POST', '/auth/login', 'login', { public: true }],
  ['GET', '/auth/me', 'me', { anyRole: true }],
  ['GET', '/rps', 'listRps'],
  ['POST', '/rps', 'uploadRps'],
  ['GET', '/rps/:rpsId', 'getRps'],
  ['POST', '/rps/:rpsId/process', 'processRps'],
  ['GET', '/rps/:rpsId/analysis', 'getRpsAnalysis'],
  ['GET', '/instructors/me/profile', 'getProfile'],
  ['PUT', '/instructors/me/profile', 'updateProfile'],
  ['GET', '/courses', 'listCourses'],
  ['POST', '/courses', 'createCourse'],
  ['GET', '/courses/:courseId', 'getCourse'],
  ['PUT', '/courses/:courseId/activity-configuration', 'updateActivityConfiguration'],
  ['POST', '/courses/:courseId/plan', 'generatePlan'],
  ['GET', '/courses/:courseId/plan', 'getPlan'],
  ['POST', '/courses/:courseId/plan/approve', 'approvePlan'],
  ['POST', '/courses/:courseId/plan/regenerate', 'regeneratePlan'],
  ['POST', '/courses/:courseId/content/generate', 'generateContent'],
  ['GET', '/courses/:courseId/content', 'getContent'],
  ['POST', '/courses/:courseId/content/:contentId/regenerate', 'regenerateContent'],
  ['POST', '/courses/:courseId/validation', 'validateContent'],
  ['GET', '/courses/:courseId/validation', 'getValidation'],
  ['GET', '/courses/:courseId/review', 'getReview'],
  ['POST', '/courses/:courseId/review/approve', 'approveContent'],
  ['POST', '/courses/:courseId/review/reject', 'rejectContent'],
  ['POST', '/courses/:courseId/execute', 'executeCourse'],
  ['GET', '/courses/:courseId/execution/:executionId', 'getExecution'],
  ['POST', '/courses/:courseId/execution/:executionId/cancel', 'cancelExecution'],
  ['POST', '/courses/:courseId/verification', 'startVerification'],
  ['GET', '/courses/:courseId/verification/:verificationId', 'getVerification'],
  ['GET', '/courses/:courseId/agent-runs', 'getAgentRuns'],
  ['GET', '/courses/:courseId/monitoring', 'getMonitoring'],
  ['GET', '/agent-runs/:runId', 'getAgentRun'],
];

function matchRoute(method, path) {
  const parts = path.split('/').filter(Boolean);
  for (const [m, pattern, name, opts = {}] of ROUTES) {
    if (m !== method) continue;
    const pp = pattern.split('/').filter(Boolean);
    if (pp.length !== parts.length) continue;
    const params = {};
    const hit = pp.every((seg, i) => {
      if (seg.startsWith(':')) {
        params[seg.slice(1)] = decodeURIComponent(parts[i]);
        return true;
      }
      return seg === parts[i];
    });
    if (hit) return { name, params, opts };
  }
  return null;
}

function userFromToken(token) {
  const id = token?.startsWith('mock-token:') ? token.slice('mock-token:'.length) : null;
  return MOCK_USERS.find((u) => u.id === id) ?? null;
}

export async function handleMockRequest({ method, path, query, body, token }) {
  if (settings.latencyMs) await sleep(settings.latencyMs);

  const route = matchRoute(method, path);
  if (!route) return fail(404, 'RESOURCE_NOT_FOUND', `Endpoint ${method} ${path} tidak tersedia.`);

  const ctx = { query, body };
  if (!route.opts.public) {
    ctx.user = userFromToken(token);
    if (!ctx.user) return fail(401, 'AUTHENTICATION_FAILED', 'Sesi berakhir, silakan login kembali.');
    // Authorization matrix (design-api.md §22): semua operasi khusus instructor.
    if (!route.opts.anyRole && ctx.user.role !== 'instructor') {
      return fail(403, 'AUTHORIZATION_DENIED', 'Operasi ini hanya untuk dosen.');
    }
  }
  if (route.params.courseId) {
    ctx.course = db.courses.find((c) => c.id === route.params.courseId);
    if (!ctx.course) return notFound('Course');
  }

  try {
    const res = handlers[route.name](route.params, ctx);
    // Salin data agar komponen tidak memodifikasi state mock secara langsung.
    return { status: res.status, data: res.data == null ? null : structuredClone(res.data) };
  } catch (e) {
    console.error('[mock]', e);
    return fail(500, 'INTERNAL_ERROR', 'Terjadi kesalahan pada mock server.');
  }
}

export function subscribeMockEvents(courseId, fn) {
  if (!listeners.has(courseId)) listeners.set(courseId, new Set());
  listeners.get(courseId).add(fn);
  return () => listeners.get(courseId)?.delete(fn);
}

// ---------------------------------------------------------------- seed

function newCourse({ rps, moodle_course_id, additional_prompt, activity_configuration }) {
  const ts = now();
  const course = {
    id: nextId('course_project'),
    rps_id: rps.id,
    name: rps.analysis.course.name,
    code: rps.analysis.course.code,
    moodle_course_id,
    additional_prompt,
    activity_configuration,
    status: 'CREATED',
    stage: null,
    progress: null,
    plan: null,
    content: {},
    validation: null,
    rejections: [],
    events: [],
    latestExecutionId: null,
    latestVerificationId: null,
    created_at: ts,
    updated_at: ts,
  };
  db.courses.push(course);
  return course;
}

export function resetMockDb() {
  timers.forEach(clearTimeout);
  timers.clear();
  listeners.clear();
  seq = {};
  db = {
    rps: [],
    courses: [],
    runs: [],
    executions: {},
    verifications: {},
    profile: {
      teaching_style: 'Interaktif dengan studi kasus dan praktikum',
      language_preference: 'Bahasa Indonesia',
      content_preference: 'Materi ringkas, banyak contoh kode',
      updated_at: now(),
    },
  };

  const rps = {
    id: nextId('rps'),
    filename: 'RPS-Pemrograman-Web-2026.pdf',
    size: 482133,
    status: 'processed',
    created_at: now(),
    analysis: null,
  };
  rps.analysis = buildRpsAnalysis(rps.id);
  db.rps.push(rps);

  // Course selesai, untuk contoh tampilan akhir.
  const done = newCourse({
    rps,
    moodle_course_id: 'IF2105-A',
    additional_prompt: 'Gunakan contoh kasus aplikasi kampus ITK.',
    activity_configuration: { learning_material: true, assignment: true, quiz: true },
  });
  done.plan = { id: nextId('plan'), course_id: done.id, version: 1, status: 'approved', instruction: null, weeks: buildPlanWeeks() };
  SAMPLE_TOPICS.forEach((topic, i) => {
    done.content[i + 1] = buildWeekContent(i + 1, topic, done.activity_configuration, i + 1 === 5 ? 1 : 0);
  });
  runValidation(done);
  done.status = 'COMPLETED';
  emit(done, 'VERIFICATION_COMPLETED', { result: 'passed' });

  // Course yang menunggu review plan.
  const pending = newCourse({
    rps,
    moodle_course_id: 'IF2105-B',
    additional_prompt: '',
    activity_configuration: { learning_material: true, assignment: true, quiz: false },
  });
  pending.plan = { id: nextId('plan'), course_id: pending.id, version: 1, status: 'draft', instruction: null, weeks: buildPlanWeeks() };
  pending.status = 'WAITING_PLAN_REVIEW';
  pending.stage = 'plan_review';
  emit(pending, 'PLANNING_COMPLETED', { version: 1 });
}

resetMockDb();
