// Konfigurasi runtime frontend, dibaca dari variabel VITE_* (lihat .env.example).

// ---- Moodle LMS (sumber data utama: course, peserta, nilai, timeline)
export const MOODLE_URL = (import.meta.env.VITE_MOODLE_URL || 'http://localhost:8080').replace(/\/+$/, '');

// Layanan resmi Moodle yang dipakai aplikasi mobile; aktifkan di
// Site administration > General > Mobile app > Enable web services for mobile devices.
export const MOODLE_SERVICE = import.meta.env.VITE_MOODLE_SERVICE || 'moodle_mobile_app';

// Default false: panggil backend/Moodle nyata. Set VITE_MOODLE_MOCK=true hanya untuk mock testing.
export const USE_MOODLE_MOCK = import.meta.env.VITE_MOODLE_MOCK === 'true';

// ---- Backend capstone (fitur Generator Konten AI untuk dosen)
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Default false: panggil FastAPI backend nyata. Set VITE_USE_MOCK=true hanya untuk mock testing.
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export const TOKEN_STORAGE_KEY = 'agentic-lms.token';
export const MOODLE_SESSION_KEY = 'agentic-lms.moodle-session';
// Preferensi UI per user; kunci lengkap: `${PREFERENCES_STORAGE_KEY}.<userId>`.
export const PREFERENCES_STORAGE_KEY = 'agentic-lms.preferences';
