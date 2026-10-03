// Konfigurasi runtime frontend, dibaca dari variabel VITE_* (lihat .env.example).

const env = import.meta.env ?? {};
// Moodle requests and credentials belong to the Backend, per moodle-integration.md.
export const API_BASE_URL = env.VITE_API_BASE_URL || '/api/v1';

// Default true supaya authentication dan service bisa dicoba tanpa backend.
export const USE_MOCK = (env.VITE_USE_MOCK ?? 'true') !== 'false';

export const TOKEN_STORAGE_KEY = 'agentic-lms.token';
