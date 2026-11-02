// Pesan untuk pengguna akhir. Detail teknis (kode HTTP, nama layanan, URL) hanya masuk ke konsol browser.

export const MSG_UNAVAILABLE = 'Layanan sedang tidak dapat diakses. Silakan coba lagi beberapa saat lagi.';
export const MSG_REQUEST_FAILED = 'Permintaan tidak dapat diproses. Silakan coba lagi.';
export const MSG_LOGIN_FAILED = 'Login gagal. Periksa username dan kata sandi Anda, lalu coba lagi.';

/** Catat detail teknis untuk pengembang (terlihat di Inspect > Console), bukan untuk pengguna. */
export function logTechnical(scope, detail) {
  console.warn(`[${scope}]`, detail);
}
