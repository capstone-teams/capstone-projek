import { api } from './apiClient';
import { formatFileSize } from '../utils/format';

// design-api.md §6 (RPS API).

// Konstanta status RPS: utils/rpsStatus.js (dipakai juga FE-11.1).

// Batas sisi klien mengikuti default backend (RPS_MAX_UPLOAD_BYTES = 20 MiB).
// DOCX ditampilkan sebagai format didukung; pemrosesannya di backend menyusul pada M03.
export const RPS_EXTENSIONS = ['pdf', 'docx'];
export const RPS_ACCEPTED_TYPES = '.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document';
export const RPS_MAX_SIZE_BYTES = 20 * 1024 * 1024;
export const RPS_MAX_SIZE_LABEL = formatFileSize(RPS_MAX_SIZE_BYTES);

/** Validasi sebelum file dikirim; mengembalikan pesan error atau null bila valid. */
export function validateRpsFile(file) {
  if (!file) return 'Pilih file RPS terlebih dahulu.';
  const extension = file.name.includes('.') ? file.name.split('.').pop().toLowerCase() : '';
  if (!RPS_EXTENSIONS.includes(extension)) return 'Format file harus PDF atau DOCX.';
  if (file.size === 0) return 'File kosong. Pilih file RPS yang berisi dokumen.';
  if (file.size > RPS_MAX_SIZE_BYTES) return `Ukuran file ${formatFileSize(file.size)} melebihi batas ${RPS_MAX_SIZE_LABEL}.`;
  return null;
}

export const isDocx = (file) => /\.docx$/i.test(file?.name ?? '');

/** POST /rps (multipart). onProgress(persen) melaporkan progres pengiriman. */
export function uploadRps(file, { onProgress } = {}) {
  const form = new FormData();
  form.append('file', file);
  return api.upload('/rps', form, { onProgress });
}

/** GET /rps: daftar RPS milik dosen yang login. */
export function listRps() {
  return api.get('/rps');
}

export function getRps(rpsId) {
  return api.get(`/rps/${rpsId}`);
}

/** POST /rps/{id}/process: 202 dijadwalkan, atau 200 + reused bila sudah pernah diproses. */
export function processRps(rpsId) {
  return api.post(`/rps/${rpsId}/process`);
}

/** POST /rps/{id}/reanalyze (§6.6): analisis ulang dari source_document; mengembalikan workflow_id. */
export function reanalyzeRps(rpsId) {
  return api.post(`/rps/${rpsId}/reanalyze`);
}

export function getRpsAnalysis(rpsId) {
  return api.get(`/rps/${rpsId}/analysis`);
}
