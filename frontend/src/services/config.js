// Konfigurasi runtime frontend, dibaca dari variabel VITE_* (lihat .env.example).

// ---- LMS (sementara sumber data course, peserta, nilai, dan timeline; belum ada API backend)
export const MOODLE_URL = (import.meta.env.VITE_MOODLE_URL || 'http://localhost:8080').replace(/\/+$/, '');

// Rujukan dokumentasi Moodle: layanan resmi aplikasi mobile, diaktifkan di
// Site administration > General > Mobile app > Enable web services for mobile devices.
export const MOODLE_SERVICE = import.meta.env.VITE_MOODLE_SERVICE || 'moodle_mobile_app';

// Default false: data Moodle lewat backend (Single Gateway). Set VITE_MOODLE_MOCK=true hanya untuk mock testing.
export const USE_MOODLE_MOCK = import.meta.env.VITE_MOODLE_MOCK === 'true';

// ---- Backend capstone (fitur Generator Konten AI untuk dosen)
// Build produksi dilayani hosting statis (Vercel) tanpa proxy Vite; /api/v1 relatif di sana
// menjawab 405. Dev/test tetap same-origin lewat proxy Vite (lihat vite.config.js).
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  || (import.meta.env.PROD ? 'https://caps.njyn.foo/api/v1' : '/api/v1');

// Default backend nyata; mock hanya bila VITE_USE_MOCK=true (dipakai test).
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

// Project kursus dari API /courses backend (GET /courses, /courses/{id}, /plan, /content): tab Generator AI
// menampilkan Ringkasan, RPS, Course Target, Rencana, Konten, Review, dan Publikasi. Endpoint aksi (membuat
// project, menyetujui rencana, generate, review, publikasi) belum ada di backend. VITE_COURSE_API=false kembali
// ke tampilan workflow saja (WorkflowLayout).
export const COURSE_API_AVAILABLE = USE_MOCK || import.meta.env.VITE_COURSE_API !== 'false';

// Fitur "Hapus" RPS yang gagal. Disembunyikan karena backend belum punya DELETE /rps/{id}; kodenya
// (useRpsLibrary.hide, tombol di RpsList) disimpan untuk berjaga-jaga. Aktifkan dengan VITE_RPS_DELETE=true
// setelah endpoint tersedia, lalu ganti isi `hide` agar memanggilnya. Mode mock (tes) selalu aktif.
export const RPS_DELETE_AVAILABLE = USE_MOCK || import.meta.env.VITE_RPS_DELETE === 'true';

export const TOKEN_STORAGE_KEY = 'agentic-lms.token';
export const MOODLE_SESSION_KEY = 'agentic-lms.moodle-session';
// Preferensi UI per user; kunci lengkap: `${PREFERENCES_STORAGE_KEY}.<userId>`.
export const PREFERENCES_STORAGE_KEY = 'agentic-lms.preferences';
