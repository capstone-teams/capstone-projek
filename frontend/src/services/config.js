// Konfigurasi Runtime Frontend (Single Gateway ke Backend FastAPI)
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
export const TOKEN_STORAGE_KEY = 'agentic-lms.token';
export const PREFERENCES_STORAGE_KEY = 'agentic-lms.preferences';

// Fitur workflow aktif penuh; course API lama dinonaktifkan
export const COURSE_API_AVAILABLE = false;
export const RPS_DELETE_AVAILABLE = import.meta.env.VITE_RPS_DELETE === 'true';
