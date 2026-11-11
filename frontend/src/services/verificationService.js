import { api } from './apiClient';
import { OPERATION_TYPE_LABELS, formatPreconditionError } from './executionService';

/** Status hasil verifikasi Moodle (VerificationStatus backend, BE-22.2). */
export const VERIFICATION_STATUS = {
  PASS: 'PASS',
  PARTIAL: 'PARTIAL',
  FAIL: 'FAIL',
  UNKNOWN: 'UNKNOWN',
};

/** Metadata tampilan untuk setiap status verifikasi Moodle. */
export const VERIFICATION_STATUS_META = {
  [VERIFICATION_STATUS.PASS]: {
    label: 'Sesuai',
    tone: 'success',
    description: 'Course di Moodle telah sesuai dengan rencana dan seluruh konten yang disetujui.',
  },
  [VERIFICATION_STATUS.PARTIAL]: {
    label: 'Sesuai dengan Catatan',
    tone: 'warning',
    description: 'Seluruh section dan konten hasil eksekusi tersedia, tetapi ada aktivitas tambahan langsung di Moodle.',
  },
  [VERIFICATION_STATUS.FAIL]: {
    label: 'Tidak Sesuai',
    tone: 'danger',
    description: 'Masih terdapat perbedaan setelah putaran perbaikan otomatis selesai.',
  },
  [VERIFICATION_STATUS.UNKNOWN]: {
    label: 'Gagal Memeriksa',
    tone: 'danger',
    description: 'Server Moodle tidak dapat dibaca saat verifikasi berlangsung.',
  },
};

/** Jenis perbedaan antara rencana/konten disetujui dan isi aktual Moodle (DiscrepancyType backend). */
export const DISCREPANCY_TYPE = {
  MISSING: 'MISSING',
  WRONG_SECTION: 'WRONG_SECTION',
  TITLE_MISMATCH: 'TITLE_MISMATCH',
  UNEXPECTED: 'UNEXPECTED',
  MAPPING_MISMATCH: 'MAPPING_MISMATCH',
};

export const DISCREPANCY_TYPE_LABELS = {
  [DISCREPANCY_TYPE.MISSING]: 'Hilang di Moodle',
  [DISCREPANCY_TYPE.WRONG_SECTION]: 'Salah section',
  [DISCREPANCY_TYPE.TITLE_MISMATCH]: 'Judul / nama berbeda',
  [DISCREPANCY_TYPE.UNEXPECTED]: 'Tambahan di Moodle',
  [DISCREPANCY_TYPE.MAPPING_MISMATCH]: 'Ketidaksesuaian mapping',
};

export const DISCREPANCY_TARGET_LABELS = {
  SECTION: 'Section mingguan',
  ACTIVITY: 'Aktivitas tambahan',
  ...OPERATION_TYPE_LABELS,
};

/** Pesan ramah pengguna untuk kode penolakan prasyarat verifikasi 409 (BE-22.2). */
export const VERIFICATION_PRECONDITION_ERRORS = {
  NO_EXECUTION_TO_VERIFY: 'Belum ada eksekusi Moodle cakupan FULL yang selesai untuk diverifikasi.',
  EXECUTION_IN_PROGRESS: 'Eksekusi ke Moodle masih berjalan. Tunggu hingga selesai sebelum menjalankan verifikasi.',
};

/**
 * Terjemahkan kode error penolakan prasyarat verifikasi (`409 INVALID_REQUEST`) menjadi teks informatif.
 * @param {any} error
 * @returns {string}
 */
export function formatVerificationPreconditionError(error) {
  return formatPreconditionError(
    error,
    VERIFICATION_PRECONDITION_ERRORS,
    'Gagal menjalankan verifikasi Moodle.',
  );
}

/**
 * POST /api/v1/workflows/{workflow_id}/verifications
 * Menjalankan verifikasi (ulang) terhadap course hasil eksekusi dan memperbaiki otomatis bila memungkinkan.
 * @param {string} workflowId
 * @param {string | null} [executionId=null]
 * @returns {Promise<any>}
 */
export function startWorkflowVerification(workflowId, executionId = null) {
  const payload = executionId ? { execution_id: executionId } : {};
  return api.post(`/workflows/${workflowId}/verifications`, payload);
}

/**
 * GET /api/v1/workflows/{workflow_id}/verifications
 * Mengambil riwayat hasil verifikasi workflow (terbaru lebih dulu).
 * @param {string} workflowId
 * @returns {Promise<Array<any>>}
 */
export function listWorkflowVerifications(workflowId) {
  return api
    .get(`/workflows/${workflowId}/verifications`)
    .then((res) => res?.items ?? (Array.isArray(res) ? res : []));
}

/**
 * GET /api/v1/workflows/{workflow_id}/verifications/{verification_id}
 * Mengambil detail satu hasil verifikasi beserta daftar perbedaan dan perbaikannya.
 * @param {string} workflowId
 * @param {string} verificationId
 * @returns {Promise<any>}
 */
export function getWorkflowVerification(workflowId, verificationId) {
  return api.get(`/workflows/${workflowId}/verifications/${verificationId}`);
}
