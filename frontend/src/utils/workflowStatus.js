import { isExamWeek } from './coursePlan';

// Status dan event workflow dari API monitoring (design-api §16-§17, BE-11.3). Dipakai tampilan status
// workflow (FE-10.1) dan dashboard dosen (FE-11.1).
//
// Berbeda dari utils/workflow.js, yang memuat status course milik API /courses (design-api §20).
//
// Backend memakai dua tingkat status:
// - lifecycle yang dikirim API: QUEUED, RUNNING, COMPLETED, FAILED (field `status`);
// - tahap yang sedang berjalan (field `stage`), mis. rps_analysis, retrying, instructor_review.
// Status tahap internal (PROCESSING_RPS, WAITING_FOR_REVIEW, RETRYING, ...) sengaja tidak dikirim API
// (src/schemas/workflow.py), jadi frontend menurunkannya dari `status` + `stage` lewat workflowStatusOf().

/** Status lifecycle yang dikirim API (`status`). */
export const WORKFLOW_API_STATUS = {
  QUEUED: 'QUEUED',
  RUNNING: 'RUNNING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
};

/** Seluruh nilai WorkflowStatus backend (src/models/workflow.py). */
export const WORKFLOW_STATUS = {
  QUEUED: 'QUEUED',
  PROCESSING_RPS: 'PROCESSING_RPS',
  ANALYZING_RPS: 'ANALYZING_RPS',
  PLANNING_COURSE: 'PLANNING_COURSE',
  GENERATING_CONTENT: 'GENERATING_CONTENT',
  VALIDATING: 'VALIDATING',
  WAITING_FOR_REVIEW: 'WAITING_FOR_REVIEW',
  EXECUTING_TO_MOODLE: 'EXECUTING_TO_MOODLE',
  VERIFYING: 'VERIFYING',
  RETRYING: 'RETRYING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
};

/**
 * label: teks; tone: warna Badge; marker: penanda visual (idle, running, review, retry, done, failed);
 * description: penjelasan singkat untuk pengguna.
 */
export const WORKFLOW_STATUS_META = {
  [WORKFLOW_STATUS.QUEUED]: { label: 'Antre', tone: 'neutral', marker: 'idle', description: 'Menunggu giliran dikerjakan.' },
  [WORKFLOW_STATUS.PROCESSING_RPS]: { label: 'Memproses RPS', tone: 'info', marker: 'running', description: 'Dokumen RPS sedang dikonversi.' },
  [WORKFLOW_STATUS.ANALYZING_RPS]: { label: 'Menganalisis RPS', tone: 'info', marker: 'running', description: 'Agent sedang menganalisis isi RPS.' },
  [WORKFLOW_STATUS.PLANNING_COURSE]: { label: 'Menyusun rencana', tone: 'info', marker: 'running', description: 'Agent sedang menyusun rencana mingguan.' },
  [WORKFLOW_STATUS.GENERATING_CONTENT]: { label: 'Membuat konten', tone: 'info', marker: 'running', description: 'Agent sedang membuat konten pembelajaran.' },
  [WORKFLOW_STATUS.VALIDATING]: { label: 'Validasi', tone: 'info', marker: 'running', description: 'Hasil agent sedang divalidasi.' },
  [WORKFLOW_STATUS.WAITING_FOR_REVIEW]: { label: 'Menunggu review Anda', tone: 'warning', marker: 'review', description: 'Perlu tindakan Anda sebelum workflow berlanjut.' },
  [WORKFLOW_STATUS.EXECUTING_TO_MOODLE]: { label: 'Eksekusi ke Moodle', tone: 'info', marker: 'running', description: 'Struktur kursus sedang dibuat di Moodle.' },
  [WORKFLOW_STATUS.VERIFYING]: { label: 'Verifikasi', tone: 'info', marker: 'running', description: 'Hasil pengiriman sedang diperiksa.' },
  [WORKFLOW_STATUS.RETRYING]: { label: 'Mencoba ulang', tone: 'warning', marker: 'retry', description: 'Tahap gagal sebagian dan sedang diperbaiki otomatis.' },
  [WORKFLOW_STATUS.COMPLETED]: { label: 'Selesai', tone: 'success', marker: 'done', description: 'Seluruh tahap selesai.' },
  [WORKFLOW_STATUS.FAILED]: { label: 'Gagal', tone: 'danger', marker: 'failed', description: 'Workflow berhenti karena kesalahan.' },
};

/** Nilai `stage` dari API (src/services/workflow/domain.py: STAGE_BY_STATUS). */
export const WORKFLOW_STAGE = {
  RPS_PROCESSING: 'rps_processing',
  RPS_ANALYSIS: 'rps_analysis',
  COURSE_PLANNING: 'course_planning',
  CONTENT_GENERATION: 'content_generation',
  VALIDATION: 'validation',
  INSTRUCTOR_REVIEW: 'instructor_review',
  MOODLE_EXECUTION: 'moodle_execution',
  VERIFICATION: 'verification',
  RETRYING: 'retrying',
};

const STATUS_BY_STAGE = {
  [WORKFLOW_STAGE.RPS_PROCESSING]: WORKFLOW_STATUS.PROCESSING_RPS,
  [WORKFLOW_STAGE.RPS_ANALYSIS]: WORKFLOW_STATUS.ANALYZING_RPS,
  [WORKFLOW_STAGE.COURSE_PLANNING]: WORKFLOW_STATUS.PLANNING_COURSE,
  [WORKFLOW_STAGE.CONTENT_GENERATION]: WORKFLOW_STATUS.GENERATING_CONTENT,
  [WORKFLOW_STAGE.VALIDATION]: WORKFLOW_STATUS.VALIDATING,
  [WORKFLOW_STAGE.INSTRUCTOR_REVIEW]: WORKFLOW_STATUS.WAITING_FOR_REVIEW,
  [WORKFLOW_STAGE.MOODLE_EXECUTION]: WORKFLOW_STATUS.EXECUTING_TO_MOODLE,
  [WORKFLOW_STAGE.VERIFICATION]: WORKFLOW_STATUS.VERIFYING,
  [WORKFLOW_STAGE.RETRYING]: WORKFLOW_STATUS.RETRYING,
};

/**
 * Urutan tahap workflow hingga M04 (DL-012): pemrosesan dan analisis RPS, course planning, validasi (rencana dan
 * konten), review dosen, pembuatan konten, lalu eksekusi ke Moodle (struktur dan FULL). Tahap yang belum dijalankan
 * backend tampil sebagai menunggu. Verifikasi menyusul begitu backend menyediakannya (BE-22.1).
 */
export const WORKFLOW_PIPELINE = [
  WORKFLOW_STAGE.RPS_PROCESSING,
  WORKFLOW_STAGE.RPS_ANALYSIS,
  WORKFLOW_STAGE.COURSE_PLANNING,
  WORKFLOW_STAGE.VALIDATION,
  WORKFLOW_STAGE.INSTRUCTOR_REVIEW,
  WORKFLOW_STAGE.CONTENT_GENERATION,
  WORKFLOW_STAGE.MOODLE_EXECUTION,
];

/** Nilai WorkflowStatus rinci dari response API: lifecycle terminal/antre dipakai apa adanya, RUNNING dibaca dari stage. */
export function workflowStatusOf(workflow) {
  const status = workflow?.status;
  if (status === WORKFLOW_API_STATUS.COMPLETED) return WORKFLOW_STATUS.COMPLETED;
  if (status === WORKFLOW_API_STATUS.FAILED) return WORKFLOW_STATUS.FAILED;
  if (status === WORKFLOW_API_STATUS.QUEUED) return WORKFLOW_STATUS.QUEUED;
  return STATUS_BY_STAGE[workflow?.stage] ?? null;
}

const UNKNOWN_META = { label: 'Berjalan', tone: 'info', marker: 'running', description: '' };

export function workflowStatusMeta(workflow) {
  const value = workflowStatusOf(workflow);
  return value ? WORKFLOW_STATUS_META[value] : { ...UNKNOWN_META, label: workflow?.status ?? 'Tidak diketahui', marker: workflow?.status ? 'running' : 'idle' };
}

/** Workflow sudah berhenti (tidak perlu dipantau lagi). */
export const isWorkflowFinished = (workflow) => [WORKFLOW_API_STATUS.COMPLETED, WORKFLOW_API_STATUS.FAILED].includes(workflow?.status);

// ---- Event

/** Kategori event (src/models/workflow_event.py: EventType, DL-011). API publik tidak mengirimnya; lihat eventTypeOf(). */
export const EVENT_TYPE = {
  PERUBAHAN_TAHAP: 'PERUBAHAN_TAHAP',
  AKTIVITAS_AGENT: 'AKTIVITAS_AGENT',
  OPERASI_MOODLE: 'OPERASI_MOODLE',
  RETRY_FIX: 'RETRY_FIX',
  ERROR_FAILURE: 'ERROR_FAILURE',
};

export const EVENT_TYPE_META = {
  [EVENT_TYPE.PERUBAHAN_TAHAP]: { label: 'Perubahan tahap', tone: 'info', marker: 'stage' },
  [EVENT_TYPE.AKTIVITAS_AGENT]: { label: 'Aktivitas agent', tone: 'neutral', marker: 'agent' },
  [EVENT_TYPE.OPERASI_MOODLE]: { label: 'Operasi kursus', tone: 'info', marker: 'stage' },
  [EVENT_TYPE.RETRY_FIX]: { label: 'Percobaan ulang', tone: 'warning', marker: 'retry' },
  [EVENT_TYPE.ERROR_FAILURE]: { label: 'Kegagalan', tone: 'danger', marker: 'failed' },
};

/** Nama event publik (design-api §17, field `event`). */
export const WORKFLOW_EVENT = {
  STARTED: 'WORKFLOW_STARTED',
  STAGE_STARTED: 'WORKFLOW_STAGE_STARTED',
  STAGE_PROGRESS: 'WORKFLOW_STAGE_PROGRESS',
  STAGE_COMPLETED: 'WORKFLOW_STAGE_COMPLETED',
  RETRY: 'WORKFLOW_RETRY',
  // Rangkaian tahap selesai dan workflow menunggu keputusan dosen (DL-012), mis. setelah course plan tersusun.
  WAITING_FOR_REVIEW: 'WORKFLOW_WAITING_FOR_REVIEW',
  // Course plan versi baru tersimpan (BE-14.3), lalu keputusan dosen atasnya (BE-14.2).
  PLAN_GENERATED: 'WORKFLOW_PLAN_GENERATED',
  PLAN_APPROVED: 'WORKFLOW_PLAN_APPROVED',
  PLAN_REJECTED: 'WORKFLOW_PLAN_REJECTED',
  // Satu operasi eksekusi ke Moodle (BE-17.1), mis. satu section mingguan.
  MOODLE_OPERATION: 'WORKFLOW_MOODLE_OPERATION',
  // Generation konten (BE-19.3): hasil per konten dan per minggu, lalu keputusan dosen (BE-19.2).
  CONTENT_VALIDATED: 'WORKFLOW_CONTENT_VALIDATED',
  CONTENT_VALIDATION_FAILED: 'WORKFLOW_CONTENT_VALIDATION_FAILED',
  CONTENT_FAILED: 'WORKFLOW_CONTENT_FAILED',
  WEEK_COMPLETED: 'WORKFLOW_WEEK_COMPLETED',
  CONTENTS_APPROVED: 'WORKFLOW_CONTENTS_APPROVED',
  CONTENTS_REJECTED: 'WORKFLOW_CONTENTS_REJECTED',
  COMPLETED: 'WORKFLOW_COMPLETED',
  FAILED: 'WORKFLOW_FAILED',
};

export const WORKFLOW_EVENT_LABELS = {
  [WORKFLOW_EVENT.STARTED]: 'Workflow dimulai',
  [WORKFLOW_EVENT.STAGE_STARTED]: 'Tahap dimulai',
  [WORKFLOW_EVENT.STAGE_PROGRESS]: 'Tahap berjalan',
  [WORKFLOW_EVENT.STAGE_COMPLETED]: 'Tahap selesai',
  [WORKFLOW_EVENT.RETRY]: 'Mencoba ulang',
  [WORKFLOW_EVENT.WAITING_FOR_REVIEW]: 'Menunggu review dosen',
  [WORKFLOW_EVENT.PLAN_GENERATED]: 'Rencana tersimpan',
  [WORKFLOW_EVENT.PLAN_APPROVED]: 'Rencana disetujui',
  [WORKFLOW_EVENT.PLAN_REJECTED]: 'Rencana ditolak',
  [WORKFLOW_EVENT.MOODLE_OPERATION]: 'Operasi Moodle',
  [WORKFLOW_EVENT.CONTENT_VALIDATED]: 'Konten lolos validasi',
  [WORKFLOW_EVENT.CONTENT_VALIDATION_FAILED]: 'Konten tidak lolos validasi',
  [WORKFLOW_EVENT.CONTENT_FAILED]: 'Konten gagal dibuat',
  [WORKFLOW_EVENT.WEEK_COMPLETED]: 'Konten minggu selesai',
  [WORKFLOW_EVENT.CONTENTS_APPROVED]: 'Konten disetujui',
  [WORKFLOW_EVENT.CONTENTS_REJECTED]: 'Konten ditolak',
  [WORKFLOW_EVENT.COMPLETED]: 'Workflow selesai',
  [WORKFLOW_EVENT.FAILED]: 'Workflow gagal',
};

/** Kategori sebuah event, diturunkan dari nama dan tahapnya (sama dengan pemetaan di orkestrator backend). */
export function eventTypeOf(event) {
  switch (event?.event) {
    case WORKFLOW_EVENT.RETRY:
      return EVENT_TYPE.RETRY_FIX;
    case WORKFLOW_EVENT.FAILED:
    case WORKFLOW_EVENT.CONTENT_VALIDATION_FAILED:
    case WORKFLOW_EVENT.CONTENT_FAILED:
      return EVENT_TYPE.ERROR_FAILURE;
    case WORKFLOW_EVENT.PLAN_GENERATED:
    case WORKFLOW_EVENT.CONTENT_VALIDATED:
    case WORKFLOW_EVENT.WEEK_COMPLETED:
      return EVENT_TYPE.AKTIVITAS_AGENT;
    case WORKFLOW_EVENT.MOODLE_OPERATION:
      return EVENT_TYPE.OPERASI_MOODLE;
    case WORKFLOW_EVENT.STAGE_PROGRESS:
      return [WORKFLOW_STAGE.MOODLE_EXECUTION, WORKFLOW_STAGE.VERIFICATION].includes(event.stage) ? EVENT_TYPE.OPERASI_MOODLE : EVENT_TYPE.AKTIVITAS_AGENT;
    default:
      return EVENT_TYPE.PERUBAHAN_TAHAP;
  }
}

// ---- Event real-time (FE-10.2)

/**
 * Batas event yang disimpan per workflow di state aplikasi. Riwayat dari GET /events dipakai utuh oleh timeline
 * (FE-10.3), jadi batasnya jauh di atas riwayat nyata (puluhan event per proses) dan hanya menjaga memori.
 */
export const MAX_WORKFLOW_EVENTS = 2000;

const timeOf = (value) => {
  const time = Date.parse(value);
  return Number.isNaN(time) ? 0 : time;
};

/** Identitas sebuah event; frame WebSocket dan GET /workflows/{id}/events memuat field yang sama. */
export const eventKey = (event) => `${event.timestamp}|${event.event}|${event.stage ?? ''}|${event.message ?? ''}`;

/** Gabungkan dua daftar event tanpa duplikat, urut waktu (stabil), dan dibatasi MAX_WORKFLOW_EVENTS. */
export function mergeEvents(current, incoming) {
  const seen = new Set();
  const merged = [...current, ...incoming].filter((event) => {
    const key = eventKey(event);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  return merged
    .map((event, index) => ({ event, index }))
    .sort((a, b) => timeOf(a.event.timestamp) - timeOf(b.event.timestamp) || a.index - b.index)
    .map(({ event }) => event)
    .slice(-MAX_WORKFLOW_EVENTS);
}

/**
 * Terapkan satu event ke snapshot workflow sehingga status, tahap, dan progres di layar langsung berubah.
 * Event yang lebih lama dari `updated_at` snapshot sudah tercermin di sana dan dilewati. Hasil ini
 * perkiraan sampai GET /workflows/{id} berikutnya, yang dipanggil setelah event akhir dan saat tersambung ulang.
 */
export function applyWorkflowEvent(workflow, event) {
  if (!workflow || !event) return workflow;
  if (event.timestamp && workflow.updated_at && timeOf(event.timestamp) < timeOf(workflow.updated_at)) return workflow;
  const next = { ...workflow, progress: event.progress ?? workflow.progress, updated_at: event.timestamp ?? workflow.updated_at };
  switch (event.event) {
    case WORKFLOW_EVENT.STARTED:
      return { ...next, status: WORKFLOW_API_STATUS.RUNNING };
    case WORKFLOW_EVENT.STAGE_STARTED:
    case WORKFLOW_EVENT.STAGE_PROGRESS:
    case WORKFLOW_EVENT.MOODLE_OPERATION:
    case WORKFLOW_EVENT.CONTENT_VALIDATED:
    case WORKFLOW_EVENT.CONTENT_VALIDATION_FAILED:
    case WORKFLOW_EVENT.CONTENT_FAILED:
    case WORKFLOW_EVENT.WEEK_COMPLETED:
      return { ...next, status: WORKFLOW_API_STATUS.RUNNING, stage: event.stage ?? workflow.stage };
    case WORKFLOW_EVENT.STAGE_COMPLETED:
      return { ...next, status: WORKFLOW_API_STATUS.RUNNING };
    case WORKFLOW_EVENT.RETRY:
      return { ...next, status: WORKFLOW_API_STATUS.RUNNING, stage: WORKFLOW_STAGE.RETRYING };
    case WORKFLOW_EVENT.WAITING_FOR_REVIEW:
      return { ...next, status: WORKFLOW_API_STATUS.RUNNING, stage: WORKFLOW_STAGE.INSTRUCTOR_REVIEW };
    case WORKFLOW_EVENT.PLAN_GENERATED:
      return { ...next, status: WORKFLOW_API_STATUS.RUNNING };
    // Keputusan dosen tidak mengubah tahap; updated_at baru membuat halaman yang memantau
    // (rencana, review konten) memuat ulang datanya.
    case WORKFLOW_EVENT.PLAN_APPROVED:
    case WORKFLOW_EVENT.PLAN_REJECTED:
    case WORKFLOW_EVENT.CONTENTS_APPROVED:
    case WORKFLOW_EVENT.CONTENTS_REJECTED:
      return next;
    case WORKFLOW_EVENT.COMPLETED:
      return { ...next, status: WORKFLOW_API_STATUS.COMPLETED, stage: null };
    case WORKFLOW_EVENT.FAILED:
      return { ...next, status: WORKFLOW_API_STATUS.FAILED, stage: null };
    default:
      return workflow;
  }
}

/**
 * Riwayat untuk timeline (FE-10.3): tiap event diberi kategori (`type`, lihat eventTypeOf) dan nomor proses
 * (`run`). Proses baru dimulai pada setiap WORKFLOW_STARTED, mis. setelah analisis ulang pada workflow yang sama.
 */
export function eventTimeline(events = []) {
  let run = 0;
  return events.map((event) => {
    if (run === 0 || event.event === WORKFLOW_EVENT.STARTED) run += 1;
    return { ...event, type: eventTypeOf(event), run };
  });
}

/** Jumlah event per kategori, untuk filter timeline. */
export function countEventTypes(timeline) {
  return timeline.reduce((counts, event) => ({ ...counts, [event.type]: (counts[event.type] ?? 0) + 1 }), {});
}

/** Event yang mengakhiri workflow; setelahnya status akhir diambil lewat HTTP. */
export const isFinalWorkflowEvent = (event) => [WORKFLOW_EVENT.COMPLETED, WORKFLOW_EVENT.FAILED].includes(event?.event);

// ---- Indikator tahap

/** Label tiap tahap pada indikator. */
export const STAGE_LABELS = {
  [WORKFLOW_STAGE.RPS_PROCESSING]: 'Pemrosesan RPS',
  [WORKFLOW_STAGE.RPS_ANALYSIS]: 'Analisis RPS',
  [WORKFLOW_STAGE.COURSE_PLANNING]: 'Penyusunan rencana',
  [WORKFLOW_STAGE.CONTENT_GENERATION]: 'Pembuatan konten',
  [WORKFLOW_STAGE.VALIDATION]: 'Validasi',
  [WORKFLOW_STAGE.INSTRUCTOR_REVIEW]: 'Review dosen',
  [WORKFLOW_STAGE.MOODLE_EXECUTION]: 'Eksekusi ke Moodle',
  [WORKFLOW_STAGE.VERIFICATION]: 'Verifikasi',
  [WORKFLOW_STAGE.RETRYING]: 'Percobaan ulang',
};

/** Keadaan satu tahap pada indikator. */
export const STAGE_STATE = {
  DONE: 'done',
  RUNNING: 'running',
  REVIEW: 'review',
  RETRYING: 'retrying',
  FAILED: 'failed',
  PENDING: 'pending',
};

export const STAGE_STATE_LABELS = {
  [STAGE_STATE.DONE]: 'Selesai',
  [STAGE_STATE.RUNNING]: 'Berjalan',
  [STAGE_STATE.REVIEW]: 'Menunggu tindakan Anda',
  [STAGE_STATE.RETRYING]: 'Mencoba ulang',
  [STAGE_STATE.FAILED]: 'Gagal',
  [STAGE_STATE.PENDING]: 'Menunggu',
};

/**
 * Keadaan setiap tahap pipeline, dari workflow (GET /workflows/{id}) dan riwayat event-nya:
 * - selesai: tahap yang punya event WORKFLOW_STAGE_COMPLETED (review dosen: pernah ada WORKFLOW_WAITING_FOR_REVIEW);
 * - berjalan, menunggu review, atau mencoba ulang: dari `stage` workflow;
 * - gagal: tahap pada event WORKFLOW_FAILED (atau tahap terakhir yang dimulai tetapi belum selesai);
 * - menunggu: sisanya, termasuk tahap yang belum dijalankan backend.
 */
export function deriveStages(workflow, events = []) {
  const stages = new Set(WORKFLOW_PIPELINE);
  events.forEach((event) => event.stage && stages.add(event.stage));
  const completed = new Set(events.filter((event) => event.event === WORKFLOW_EVENT.STAGE_COMPLETED).map((event) => event.stage));
  // Review dosen tidak punya event selesai: review yang pernah ditunggu dan kini tidak lagi aktif dianggap selesai.
  if (events.some((event) => event.event === WORKFLOW_EVENT.WAITING_FOR_REVIEW)) completed.add(WORKFLOW_STAGE.INSTRUCTOR_REVIEW);
  const lastRetry = [...events].reverse().find((event) => event.event === WORKFLOW_EVENT.RETRY);
  const failedEvent = [...events].reverse().find((event) => event.event === WORKFLOW_EVENT.FAILED);
  const lastStarted = [...events].reverse().find((event) => event.event === WORKFLOW_EVENT.STAGE_STARTED);
  const running = workflow?.status === WORKFLOW_API_STATUS.RUNNING;
  const failed = workflow?.status === WORKFLOW_API_STATUS.FAILED;
  const failedStage = failed ? (failedEvent?.stage ?? (lastStarted && !completed.has(lastStarted.stage) ? lastStarted.stage : null)) : null;
  const retryingStage = running && workflow.stage === WORKFLOW_STAGE.RETRYING ? lastRetry?.stage : null;

  const stateOf = (stage) => {
    if (stage === failedStage) return STAGE_STATE.FAILED;
    if (stage === retryingStage) return STAGE_STATE.RETRYING;
    if (running && stage === workflow.stage) return stage === WORKFLOW_STAGE.INSTRUCTOR_REVIEW ? STAGE_STATE.REVIEW : STAGE_STATE.RUNNING;
    if (completed.has(stage)) return STAGE_STATE.DONE;
    return STAGE_STATE.PENDING;
  };

  const ordered = [...WORKFLOW_PIPELINE, ...[...stages].filter((stage) => !WORKFLOW_PIPELINE.includes(stage) && stage !== WORKFLOW_STAGE.RETRYING)];
  return ordered.map((stage) => ({ stage, label: STAGE_LABELS[stage] ?? stage, state: stateOf(stage) }));
}

/** Tahap yang sedang menunggu tindakan dosen (WAITING_FOR_REVIEW), bila ada. */
export const needsInstructorAction = (workflow) => workflowStatusOf(workflow) === WORKFLOW_STATUS.WAITING_FOR_REVIEW;

// ---- Course planning (BE-14.3, FE-12.1)

/** Tahap backend yang dijalankan saat course plan disusun: PLANNING_COURSE lalu VALIDATING. */
export const COURSE_PLAN_STAGES = [WORKFLOW_STAGE.COURSE_PLANNING, WORKFLOW_STAGE.VALIDATION];

const lastEvent = (events, name) => [...events].reverse().find((event) => event.event === name);

/**
 * Tahap penyusunan course plan yang sedang berjalan: PLANNING_COURSE, VALIDATING, atau RETRYING (percobaan ulang
 * pada salah satu tahap itu); null bila workflow tidak sedang menyusun rencana.
 */
export function coursePlanProgressOf(workflow, events = []) {
  const status = workflowStatusOf(workflow);
  if (status === WORKFLOW_STATUS.PLANNING_COURSE || status === WORKFLOW_STATUS.VALIDATING) return status;
  if (status !== WORKFLOW_STATUS.RETRYING) return null;
  const retry = lastEvent(events, WORKFLOW_EVENT.RETRY);
  return !retry || COURSE_PLAN_STAGES.includes(retry.stage) ? WORKFLOW_STATUS.RETRYING : null;
}

/** Tahap yang sedang dicoba ulang (course_planning atau validation) saat status RETRYING. */
export const retryingStageOf = (events = []) => lastEvent(events, WORKFLOW_EVENT.RETRY)?.stage ?? WORKFLOW_STAGE.COURSE_PLANNING;

/** Event WORKFLOW_FAILED terakhir bila kegagalan workflow terjadi saat menyusun atau memvalidasi course plan. */
export function coursePlanFailureOf(workflow, events = []) {
  if (workflow?.status !== WORKFLOW_API_STATUS.FAILED) return null;
  const index = events.map((event) => event.event === WORKFLOW_EVENT.FAILED).lastIndexOf(true);
  const failed = events[index];
  if (!failed || !COURSE_PLAN_STAGES.includes(failed.stage)) return null;
  // Tahap validasi juga dipakai konten (M04): kegagalannya milik rencana hanya bila tahap kerja sebelumnya course planning.
  if (failed.stage === WORKFLOW_STAGE.VALIDATION && workStageBefore(events, index) !== WORKFLOW_STAGE.COURSE_PLANNING) return null;
  return failed;
}

// ---- Tindakan yang ditunggu saat WAITING_FOR_REVIEW (DL-012)

/** Tindakan dosen yang ditunggu workflow; dibedakan dari event terakhir karena statusnya sama-sama WAITING_FOR_REVIEW. */
export const AWAITED_ACTION = {
  START_PLANNING: 'START_PLANNING',
  REVIEW_PLAN: 'REVIEW_PLAN',
  REVISE_PLAN: 'REVISE_PLAN',
  EXECUTE_STRUCTURE: 'EXECUTE_STRUCTURE',
  GENERATE_CONTENT: 'GENERATE_CONTENT',
  REVIEW_CONTENT: 'REVIEW_CONTENT',
  REVISE_CONTENT: 'REVISE_CONTENT',
  EXECUTE_FULL: 'EXECUTE_FULL',
};

/** title/description untuk pengguna; page: tab Generator AI tujuan tautan cepat; secondary: tautan tambahan. */
export const AWAITED_ACTION_META = {
  [AWAITED_ACTION.START_PLANNING]: { title: 'Mulai course planning', description: 'Analisis RPS selesai. Mulai penyusunan course plan dari hasil analisis.', page: 'plan', linkLabel: 'Buka halaman Rencana' },
  [AWAITED_ACTION.REVIEW_PLAN]: { title: 'Review course plan', description: 'Course plan selesai disusun. Periksa, lalu setujui atau tolak dengan catatan revisi.', page: 'plan', linkLabel: 'Buka Plan Review' },
  [AWAITED_ACTION.REVISE_PLAN]: { title: 'Regenerasi course plan', description: 'Course plan ditolak. Susun ulang rencana berdasarkan catatan revisi.', page: 'plan', linkLabel: 'Buka Plan Review' },
  [AWAITED_ACTION.EXECUTE_STRUCTURE]: { title: 'Eksekusi struktur', description: 'Course plan disetujui. Buat struktur mingguan di kursus Moodle target.', page: 'publish', linkLabel: 'Buka halaman eksekusi' },
  [AWAITED_ACTION.GENERATE_CONTENT]: { title: 'Generate konten', description: 'Struktur kursus sudah dibuat di Moodle. Lanjutkan dengan generate konten mingguan.', page: 'content', linkLabel: 'Buka halaman Konten' },
  [AWAITED_ACTION.REVIEW_CONTENT]: { title: 'Review konten', description: 'Konten mingguan selesai dibuat dan divalidasi. Periksa, lalu setujui, tolak, atau regenerasi konten.', page: 'review', linkLabel: 'Buka halaman Review' },
  [AWAITED_ACTION.REVISE_CONTENT]: { title: 'Regenerasi konten', description: 'Sebagian konten ditolak. Regenerasi konten tersebut berdasarkan catatan revisi.', page: 'review', linkLabel: 'Buka halaman Review' },
  [AWAITED_ACTION.EXECUTE_FULL]: {
    title: 'Eksekusi FULL',
    description: 'Konten telah disetujui. Pastikan seluruh konten disetujui, lalu kirim struktur dan konten ke Moodle.',
    page: 'publish',
    linkLabel: 'Buka halaman eksekusi FULL',
    secondary: { page: 'review', label: 'Buka halaman Review' },
  },
};

const completedStage = (event, stages) => event.event === WORKFLOW_EVENT.STAGE_COMPLETED && stages.includes(event.stage);
const CONTENT_RESULT_EVENTS = [WORKFLOW_EVENT.CONTENT_VALIDATED, WORKFLOW_EVENT.CONTENT_VALIDATION_FAILED, WORKFLOW_EVENT.CONTENT_FAILED, WORKFLOW_EVENT.WEEK_COMPLETED];
// Operasi activity eksekusi FULL berpesan "Minggu N - Jenis ..."; operasi section hanya "Minggu N ...".
const isActivityOperation = (event) => / - (Learning Material|Learning Resource|Assignment|Quiz) /.test(event.message ?? '');

/** Tahap kerja (bukan validasi) yang terakhir dimulai sebelum indeks tertentu: validasi milik rencana atau konten. */
function workStageBefore(events, index) {
  for (let i = index - 1; i >= 0; i -= 1) {
    const event = events[i];
    if (event.event === WORKFLOW_EVENT.STAGE_STARTED && event.stage && event.stage !== WORKFLOW_STAGE.VALIDATION) return event.stage;
  }
  return null;
}

/** Cek apakah run eksekusi Moodle berakhir pada operasi activity (FULL) dan bukan struktur saja. */
function isFullExecutionRunBefore(events, index) {
  for (let i = index - 1; i >= 0; i -= 1) {
    const prev = events[i];
    if (prev.event === WORKFLOW_EVENT.MOODLE_OPERATION) {
      if (isActivityOperation(prev)) return true;
    } else if (
      (prev.event === WORKFLOW_EVENT.STAGE_STARTED && prev.stage === WORKFLOW_STAGE.MOODLE_EXECUTION)
      || prev.event === WORKFLOW_EVENT.CONTENTS_APPROVED
      || prev.event === WORKFLOW_EVENT.PLAN_APPROVED
    ) {
      return false;
    }
  }
  return false;
}

/**
 * Tindakan yang ditunggu workflow WAITING_FOR_REVIEW, dari event terakhir yang menandai sebuah tahap:
 * - M04: konten disetujui -> eksekusi FULL; konten ditolak -> regenerasi konten; konten selesai dibuat/divalidasi
 *   -> review konten; eksekusi FULL selesai -> verifikasi (belum tersedia, null);
 * - M03: eksekusi struktur selesai -> generate konten; rencana disetujui -> eksekusi struktur; rencana ditolak ->
 *   regenerasi; rencana tersusun -> review course plan; analisis RPS selesai -> mulai course planning.
 * null bila workflow tidak sedang menunggu dosen atau tindakannya tidak dapat ditentukan.
 */
export function awaitedActionOf(workflow, events = []) {
  if (!needsInstructorAction(workflow)) return null;
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event.event === WORKFLOW_EVENT.MOODLE_OPERATION) return isActivityOperation(event) ? null : AWAITED_ACTION.GENERATE_CONTENT;
    if (completedStage(event, [WORKFLOW_STAGE.MOODLE_EXECUTION])) return isFullExecutionRunBefore(events, index) ? null : AWAITED_ACTION.GENERATE_CONTENT;
    if (event.event === WORKFLOW_EVENT.CONTENTS_APPROVED) return AWAITED_ACTION.EXECUTE_FULL;
    if (event.event === WORKFLOW_EVENT.CONTENTS_REJECTED) return AWAITED_ACTION.REVISE_CONTENT;
    if (CONTENT_RESULT_EVENTS.includes(event.event) || completedStage(event, [WORKFLOW_STAGE.CONTENT_GENERATION])) return AWAITED_ACTION.REVIEW_CONTENT;
    if (completedStage(event, [WORKFLOW_STAGE.VALIDATION])) {
      return workStageBefore(events, index) === WORKFLOW_STAGE.CONTENT_GENERATION ? AWAITED_ACTION.REVIEW_CONTENT : AWAITED_ACTION.REVIEW_PLAN;
    }
    if (event.event === WORKFLOW_EVENT.PLAN_APPROVED) return AWAITED_ACTION.EXECUTE_STRUCTURE;
    if (event.event === WORKFLOW_EVENT.PLAN_REJECTED) return AWAITED_ACTION.REVISE_PLAN;
    if (event.event === WORKFLOW_EVENT.PLAN_GENERATED || completedStage(event, [WORKFLOW_STAGE.COURSE_PLANNING])) return AWAITED_ACTION.REVIEW_PLAN;
    if (completedStage(event, [WORKFLOW_STAGE.RPS_ANALYSIS])) return AWAITED_ACTION.START_PLANNING;
  }
  return null;
}

// ---- Stepper generator AI (navigasi utama 7 langkah pada AiCourseLayout)

export const WORKFLOW_STEPPER_STEPS = [
  { key: 'rps', label: 'RPS', to: 'rps' },
  { key: 'plan', label: 'Rencana', to: 'plan' },
  { key: 'content', label: 'Konten', to: 'content' },
  { key: 'review', label: 'Review', to: 'review' },
  { key: 'execution', label: 'Eksekusi Moodle', to: 'publish' },
  { key: 'verification', label: 'Verifikasi', to: 'verification' },
  { key: 'done', label: 'Selesai', to: '' },
];

/**
 * Tahap dapat dibuka bila sudah tercapai: tahap yang selesai dan tahap yang sedang berjalan. Tahap berikutnya
 * terkunci sampai tahap sebelumnya selesai (mis. Rencana belum dapat dibuka selama RPS belum selesai dianalisis).
 */
export function isStepReachable(index, { current, finished }) {
  return finished || index <= current;
}

/** Kunci langkah stepper dari path halaman Generator AI yang sedang dibuka (null untuk Ringkasan/Workflow). */
export function viewingKeyFromPath(pathname) {
  const clean = String(pathname || '').replace(/\/+$/, '');
  if (clean.endsWith('/rps')) return 'rps';
  if (clean.endsWith('/plan')) return 'plan';
  if (clean.endsWith('/content')) return 'content';
  if (clean.endsWith('/review')) return 'review';
  if (clean.endsWith('/publish')) return 'execution';
  if (clean.endsWith('/verification')) return 'verification';
  return null;
}

function stepperIndexForStage(stage, events = []) {
  switch (stage) {
    case WORKFLOW_STAGE.RPS_PROCESSING:
    case WORKFLOW_STAGE.RPS_ANALYSIS:
      return 0;
    case WORKFLOW_STAGE.COURSE_PLANNING:
      return 1;
    case WORKFLOW_STAGE.CONTENT_GENERATION:
      return 2;
    case WORKFLOW_STAGE.VALIDATION:
      return isContentGenerationActiveContext(events) ? 2 : 1;
    case WORKFLOW_STAGE.MOODLE_EXECUTION:
      return 4;
    case WORKFLOW_STAGE.VERIFICATION:
      return 5;
    default:
      return 0;
  }
}

function eventMilestoneIndex(workflow, events = []) {
  const hasContentHistory = events.some(
    (ev) => CONTENT_RESULT_EVENTS.includes(ev?.event)
      || ev?.event === WORKFLOW_EVENT.CONTENTS_APPROVED
      || ev?.event === WORKFLOW_EVENT.CONTENTS_REJECTED,
  );
  const action = awaitedActionOf(workflow, events);
  switch (action) {
    case AWAITED_ACTION.START_PLANNING:
    case AWAITED_ACTION.REVIEW_PLAN:
    case AWAITED_ACTION.REVISE_PLAN:
      return 1;
    case AWAITED_ACTION.EXECUTE_STRUCTURE:
    case AWAITED_ACTION.GENERATE_CONTENT:
      return hasContentHistory ? 3 : 2;
    case AWAITED_ACTION.REVIEW_CONTENT:
    case AWAITED_ACTION.REVISE_CONTENT:
      return 3;
    case AWAITED_ACTION.EXECUTE_FULL:
      return 4;
    default: {
      const hadFullExecution = events.some((ev) => ev?.event === WORKFLOW_EVENT.MOODLE_OPERATION && isActivityOperation(ev));
      if (hadFullExecution) return 5;
      if (hasContentHistory) return 3;
      if (events.some((ev) => ev?.event === WORKFLOW_EVENT.PLAN_APPROVED)) return 2;
      if (events.some((ev) => completedStage(ev, [WORKFLOW_STAGE.RPS_ANALYSIS]) || ev?.event === WORKFLOW_EVENT.PLAN_GENERATED)) return 1;
      return 0;
    }
  }
}

/**
 * Menurunkan langkah aktif (0..6) dan status selesai untuk 7-step WorkflowStepper dari snapshot
 * workflow nyata (`status` + `stage`), riwayat event, serta data aktual `{ plan, contents, executions, verifications }`.
 * Langkah dijaga monoton terhadap pencapaian deliverable nyata agar tidak mundur ke "Konten" saat
 * konten mingguan sudah ada (mis. sedang review parsial, regenerasi item, atau pasca-eksekusi struktur).
 */
export function deriveStepperState(workflow, events = [], { plan = null, contents = null, executions = null, verifications = null } = {}) {
  if (!workflow) return { current: 0, finished: false };
  const latestVerification = Array.isArray(verifications) && verifications.length > 0 ? verifications[0] : null;
  const verificationPassed = Boolean(
    latestVerification && (latestVerification.matches === true || latestVerification.status === 'PASS'),
  );
  if (workflow.status === WORKFLOW_API_STATUS.COMPLETED || verificationPassed) {
    return { current: 6, finished: true };
  }

  const hasPlan = Boolean(plan);
  const planApproved = plan?.status === 'APPROVED';
  const hasContentsList = Array.isArray(contents);
  const hasContents = hasContentsList && contents.length > 0;
  const allContentsApproved = hasContents
    && contents.every((item) => item?.status === 'APPROVED' || item?.status === 'EXECUTED');
  const hasExecutionsList = Array.isArray(executions);
  const hasFullExecutionCompleted = hasExecutionsList
    ? executions.some((ex) => ex?.scope === 'FULL' && (ex?.status === 'SUCCESS' || ex?.status === 'PARTIAL_SUCCESS'))
    : events.some((ev) => ev?.event === WORKFLOW_EVENT.MOODLE_OPERATION && isActivityOperation(ev));
  const rpsAnalyzed = hasPlan
    || hasContents
    || (hasExecutionsList && executions.length > 0)
    || events.some((ev) => completedStage(ev, [WORKFLOW_STAGE.RPS_ANALYSIS]) || ev?.event === WORKFLOW_EVENT.PLAN_APPROVED);

  let milestone = 0;
  if (hasFullExecutionCompleted) {
    milestone = 5;
  } else if (hasContentsList) {
    if (allContentsApproved) milestone = 4;
    else if (hasContents) milestone = 3;
    else if (planApproved || events.some((ev) => ev?.event === WORKFLOW_EVENT.PLAN_APPROVED)) milestone = 2;
    else if (rpsAnalyzed) milestone = 1;
  } else {
    milestone = eventMilestoneIndex(workflow, events);
  }

  if (workflow.status === WORKFLOW_API_STATUS.FAILED) {
    const failed = lastEvent(events, WORKFLOW_EVENT.FAILED);
    const started = lastEvent(events, WORKFLOW_EVENT.STAGE_STARTED);
    const stageStep = stepperIndexForStage(failed?.stage ?? started?.stage, events);
    return { current: Math.max(milestone, stageStep), finished: false };
  }

  if (workflow.status === WORKFLOW_API_STATUS.QUEUED) {
    const started = lastEvent(events, WORKFLOW_EVENT.STAGE_STARTED);
    const stageStep = started ? stepperIndexForStage(started.stage, events) : 0;
    return { current: Math.max(milestone, stageStep), finished: false };
  }

  if (workflow.stage === WORKFLOW_STAGE.RETRYING) {
    const retry = lastEvent(events, WORKFLOW_EVENT.RETRY);
    return { current: Math.max(milestone, stepperIndexForStage(retry?.stage, events)), finished: false };
  }

  if (workflow.stage === WORKFLOW_STAGE.INSTRUCTOR_REVIEW) {
    return { current: Math.max(milestone, eventMilestoneIndex(workflow, [])), finished: false };
  }

  return { current: Math.max(milestone, stepperIndexForStage(workflow.stage, events)), finished: false };
}

// ---- Content generation (BE-19.3, FE-16)

/** Tahap backend yang dijalankan saat konten disusun: GENERATING_CONTENT lalu VALIDATING. */
export const CONTENT_GENERATION_STAGES = [WORKFLOW_STAGE.CONTENT_GENERATION, WORKFLOW_STAGE.VALIDATION];

/** Workflow sedang menjalankan proses background di luar tahap tunggu review dosen. */
export function isWorkflowBusy(workflow) {
  if (!workflow) return false;
  if (workflow.status === WORKFLOW_API_STATUS.QUEUED) return true;
  return workflow.status === WORKFLOW_API_STATUS.RUNNING && workflow.stage !== WORKFLOW_STAGE.INSTRUCTOR_REVIEW;
}

const CONTENT_STAGE_EVENTS = [
  WORKFLOW_EVENT.CONTENT_VALIDATED,
  WORKFLOW_EVENT.CONTENT_VALIDATION_FAILED,
  WORKFLOW_EVENT.CONTENT_FAILED,
  WORKFLOW_EVENT.WEEK_COMPLETED,
];

function isContentGenerationActiveContext(events = []) {
  for (const event of [...events].reverse()) {
    if (CONTENT_STAGE_EVENTS.includes(event.event)) return true;
    if (event.event === WORKFLOW_EVENT.STAGE_STARTED) {
      if (event.stage === WORKFLOW_STAGE.CONTENT_GENERATION) return true;
      if (event.stage === WORKFLOW_STAGE.COURSE_PLANNING) return false;
    }
    if (event.stage === WORKFLOW_STAGE.CONTENT_GENERATION) return true;
  }
  return false;
}

/**
 * Tahap content generation yang sedang berjalan: GENERATING_CONTENT, VALIDATING, atau RETRYING
 * pada tahap content_generation; null bila workflow tidak sedang membuat konten.
 */
export function contentGenerationProgressOf(workflow, events = []) {
  const status = workflowStatusOf(workflow);
  if (status === WORKFLOW_STATUS.GENERATING_CONTENT) return status;
  if (status === WORKFLOW_STATUS.RETRYING) {
    const retry = lastEvent(events, WORKFLOW_EVENT.RETRY);
    return retry?.stage === WORKFLOW_STAGE.CONTENT_GENERATION ? WORKFLOW_STATUS.RETRYING : null;
  }
  if (status === WORKFLOW_STATUS.VALIDATING) {
    return isContentGenerationActiveContext(events) ? WORKFLOW_STATUS.VALIDATING : null;
  }
  return null;
}

/** Event WORKFLOW_FAILED terakhir bila kegagalan workflow terjadi pada tahap content generation. */
export function contentGenerationFailureOf(workflow, events = []) {
  if (workflow?.status !== WORKFLOW_API_STATUS.FAILED) return null;
  const failed = lastEvent(events, WORKFLOW_EVENT.FAILED);
  if (!failed) return null;
  if (failed.stage === WORKFLOW_STAGE.CONTENT_GENERATION) return failed;
  if (failed.stage === WORKFLOW_STAGE.VALIDATION && isContentGenerationActiveContext(events)) return failed;
  return null;
}

// ---- Matriks progres generation per minggu × jenis konten (FE-16.2)

export const CONTENT_CELL_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  RETRYING: 'retrying',
  COMPLETED: 'completed',
  FAILED: 'failed',
  SKIPPED: 'skipped',
  EXAM: 'exam',
};

const CONTENT_KIND_ORDER = ['LEARNING_MATERIAL', 'RESOURCE', 'ASSIGNMENT', 'QUIZ'];

const CONTENT_LABEL_TO_KIND = {
  'learning material': 'LEARNING_MATERIAL',
  'learning resource': 'RESOURCE',
  assignment: 'ASSIGNMENT',
  quiz: 'QUIZ',
};

const ITEM_EVENT_PATTERN = /^Minggu\s+(\d+)\s*-\s*(Learning Material|Learning Resource|Assignment|Quiz)\s+(.+?)\.?$/i;
const WEEK_COMPLETED_PATTERN = /^Minggu\s+(\d+)\s+selesai(?:\s*:|\.)?/i;

function isKindApplicableToWeek(week, kind) {
  const weekType = String(week?.week_type ?? 'regular').toLowerCase();
  if (weekType === 'kuis' || weekType === 'quiz') return kind === 'QUIZ';
  if (weekType === 'uts' || weekType === 'uas') return false;
  return kind !== 'QUIZ';
}

/**
 * Parse satu event BE-19.3 (format pesan dari orchestrator.py / generation.py) menjadi identitas sel matriks.
 * Mengembalikan `{ weekNumber, kind, status }` untuk event item, `{ weekNumber, weekCompleted: true }` untuk
 * WORKFLOW_WEEK_COMPLETED, atau null bila bukan event progres item/minggu konten.
 */
export function parseContentEventMessage(event) {
  const message = String(event?.message ?? '').trim();
  if (!message) return null;

  if (event?.event === WORKFLOW_EVENT.WEEK_COMPLETED) {
    const match = message.match(WEEK_COMPLETED_PATTERN);
    return match ? { weekNumber: Number(match[1]), weekCompleted: true } : null;
  }

  const itemMatch = message.match(ITEM_EVENT_PATTERN);
  if (!itemMatch) return null;

  const weekNumber = Number(itemMatch[1]);
  const kind = CONTENT_LABEL_TO_KIND[itemMatch[2].toLowerCase()];
  const verb = itemMatch[3].toLowerCase();
  if (!kind) return null;

  if (event?.event === WORKFLOW_EVENT.RETRY || verb === 'diperbaiki') {
    return { weekNumber, kind, status: CONTENT_CELL_STATUS.RETRYING };
  }
  if (
    event?.event === WORKFLOW_EVENT.CONTENT_FAILED
    || event?.event === WORKFLOW_EVENT.CONTENT_VALIDATION_FAILED
    || verb.startsWith('gagal')
  ) {
    return { weekNumber, kind, status: CONTENT_CELL_STATUS.FAILED };
  }
  if (event?.event === WORKFLOW_EVENT.CONTENT_VALIDATED || verb === 'selesai') {
    return { weekNumber, kind, status: CONTENT_CELL_STATUS.COMPLETED };
  }
  return { weekNumber, kind, status: CONTENT_CELL_STATUS.PROCESSING };
}

/** Mengambil slice event dari run content generation terbaru agar event run lama tidak menimpa status baru. */
export function latestContentGenerationRunEvents(events = []) {
  let startIndex = -1;
  for (let i = events.length - 1; i >= 0; i -= 1) {
    if (events[i]?.event === WORKFLOW_EVENT.STAGE_STARTED && events[i]?.stage === WORKFLOW_STAGE.CONTENT_GENERATION) {
      startIndex = i;
      break;
    }
  }
  if (startIndex >= 0) {
    return {
      runEvents: events.slice(startIndex),
      runStartTime: timeOf(events[startIndex]?.timestamp),
    };
  }
  return { runEvents: events, runStartTime: 0 };
}

/** Apakah workflow sudah punya data/riwayat aktivitas content generation sehingga matriks FE-16.2 perlu tampil. */
export function hasContentGenerationActivity(workflow, events = [], contents = []) {
  if (contents.length > 0) return true;
  if (contentGenerationProgressOf(workflow, events) || contentGenerationFailureOf(workflow, events)) return true;
  return events.some(
    (event) => CONTENT_STAGE_EVENTS.includes(event?.event) || event?.stage === WORKFLOW_STAGE.CONTENT_GENERATION,
  );
}

function recordCellStatus(record) {
  const validationStatus = record?.validation?.status;
  if (validationStatus === 'PASSED') return CONTENT_CELL_STATUS.COMPLETED;
  if (validationStatus === 'FAILED') return CONTENT_CELL_STATUS.FAILED;
  return CONTENT_CELL_STATUS.PROCESSING;
}

/**
 * Membangun baris matriks (minggu × 4 jenis konten) dengan menggabungkan data awal GET .../contents
 * dan overlay real-time event AKTIVITAS_AGENT / RETRY_FIX (FE-16.2).
 */
export function deriveContentMatrixRows(plan, contents = [], events = [], workflow = null) {
  const weeks = [...(plan?.weeks ?? [])].sort((a, b) => a.week_number - b.week_number);
  const byWeekAndKind = new Map();
  const weeksWithStoredContent = new Set();

  contents.forEach((item) => {
    if (item?.week_number != null && item?.kind) {
      byWeekAndKind.set(`${item.week_number}:${item.kind}`, item);
      weeksWithStoredContent.add(item.week_number);
    }
  });

  const { runEvents, runStartTime } = latestContentGenerationRunEvents(events);
  const liveByCell = new Map();
  const completedWeeksInRun = new Set();

  runEvents.forEach((event) => {
    const parsed = parseContentEventMessage(event);
    if (!parsed) return;
    if (parsed.weekCompleted) {
      completedWeeksInRun.add(parsed.weekNumber);
      return;
    }
    liveByCell.set(`${parsed.weekNumber}:${parsed.kind}`, {
      status: parsed.status,
      timestamp: event.timestamp,
    });
  });

  const generating = Boolean(contentGenerationProgressOf(workflow, events));

  return weeks.map((week) => {
    const exam = isExamWeek(week);
    const weekDone = completedWeeksInRun.has(week.week_number) || (!generating && weeksWithStoredContent.has(week.week_number));
    const cells = {};

    CONTENT_KIND_ORDER.forEach((kind) => {
      const key = `${week.week_number}:${kind}`;
      const record = byWeekAndKind.get(key) ?? null;
      const live = liveByCell.get(key) ?? null;

      // Overlay event run terbaru bila belum ada record, atau run baru dimulai sesudah updated_at record lama,
      // atau saat sedang berjalan tanpa timestamp STAGE_STARTED dan event setara/lebih baru dari record.
      const useLive = Boolean(live) && (
        !record
        || (runStartTime > 0 && runStartTime > timeOf(record.updated_at))
        || (generating && runStartTime === 0 && timeOf(live.timestamp) >= timeOf(record.updated_at))
      );

      if (useLive) {
        cells[kind] = { kind, status: live.status, record };
        return;
      }
      if (record) {
        cells[kind] = { kind, status: recordCellStatus(record), record };
        return;
      }
      if (exam) {
        cells[kind] = { kind, status: CONTENT_CELL_STATUS.EXAM };
        return;
      }
      if (!isKindApplicableToWeek(week, kind)) {
        cells[kind] = { kind, status: CONTENT_CELL_STATUS.SKIPPED, reason: 'week_type' };
        return;
      }
      if (weekDone) {
        cells[kind] = { kind, status: CONTENT_CELL_STATUS.SKIPPED, reason: 'not_scheduled' };
        return;
      }
      cells[kind] = { kind, status: CONTENT_CELL_STATUS.PENDING };
    });

    const rowExam = exam && !Object.values(cells).some((cell) => cell.status !== CONTENT_CELL_STATUS.EXAM);
    return { week, exam: rowExam, cells };
  });
}
