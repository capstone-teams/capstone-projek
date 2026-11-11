/** Klien HTTP mengarah ke backend nyata lewat proxy Vite (`/api/v1`) atau origin yang dikonfigurasi. */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  ?? `${(import.meta.env.VITE_BACKEND_URL || '').replace(/\/$/, '')}/api/v1`;

export const TOKEN_STORAGE_KEY = 'agentic_lms.backend_token';
export const PREFERENCES_STORAGE_KEY = 'agentic_lms.preferences';

// Flag fitur opsional / belum tersedia di seluruh environment backend.
export const COURSE_API_AVAILABLE = true;
export const RPS_DELETE_AVAILABLE = import.meta.env.VITE_RPS_DELETE === 'true';
