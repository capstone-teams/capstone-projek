// Status pemrosesan RPS: enum kanonik backend (huruf besar, design-api §6.5) beserta label
// Bahasa Indonesia dan penanda visual. Dipakai daftar RPS (FE-08.1/08.2) dan dashboard dosen (FE-11.1).
//
// Urutan normal: UPLOADED → PROCESSING (konversi Docling) → PROCESSED → ANALYZING → ANALYZED.
// FAILED dapat terjadi pada konversi maupun analisis. ANALYZING/ANALYZED terbit bersama BE-08.2.

export const RPS_STATUS = {
  UPLOADED: 'UPLOADED',
  PROCESSING: 'PROCESSING',
  PROCESSED: 'PROCESSED',
  ANALYZING: 'ANALYZING',
  ANALYZED: 'ANALYZED',
  FAILED: 'FAILED',
};

/**
 * label: teks badge; tone: warna Badge; marker: penanda visual (running = indikator berputar);
 * description: penjelasan singkat untuk pengguna.
 */
export const RPS_STATUS_META = {
  [RPS_STATUS.UPLOADED]: { label: 'Diunggah', tone: 'neutral', marker: 'idle', description: 'Menunggu pemrosesan dimulai.' },
  [RPS_STATUS.PROCESSING]: { label: 'Diproses', tone: 'info', marker: 'running', description: 'Dokumen sedang dikonversi.' },
  [RPS_STATUS.PROCESSED]: { label: 'Siap dianalisis', tone: 'info', marker: 'idle', description: 'Dokumen terkonversi; menunggu analisis.' },
  [RPS_STATUS.ANALYZING]: { label: 'Dianalisis', tone: 'info', marker: 'running', description: 'Agent sedang menganalisis isi RPS.' },
  [RPS_STATUS.ANALYZED]: { label: 'Selesai dianalisis', tone: 'success', marker: 'done', description: 'Hasil analisis siap dipakai.' },
  [RPS_STATUS.FAILED]: { label: 'Gagal', tone: 'danger', marker: 'failed', description: 'Pemrosesan berhenti karena kesalahan.' },
};

export function rpsStatusMeta(status) {
  return RPS_STATUS_META[status] ?? { label: status ?? 'Tidak diketahui', tone: 'neutral', marker: 'idle', description: '' };
}

/**
 * Masih berjalan di background sehingga perlu dipantau. PROCESSED dihitung berjalan hanya bila
 * workflow analisis sudah dibuat (workflow_id, BE-11.2); tanpa workflow, PROCESSED adalah akhir
 * pemrosesan pada backend yang belum memiliki tahap analisis.
 */
export function isRpsInProgress(rps) {
  if ([RPS_STATUS.UPLOADED, RPS_STATUS.PROCESSING, RPS_STATUS.ANALYZING].includes(rps?.status)) return true;
  return rps?.status === RPS_STATUS.PROCESSED && !!rps.workflow_id;
}

/** RPS yang dapat dipakai generator kursus. PROCESSED tetap diterima selama backend belum menganalisis. */
export const RPS_READY = [RPS_STATUS.PROCESSED, RPS_STATUS.ANALYZED];
