import { api, getToken, setToken } from './apiClient';
import { ROLE_FROM_BACKEND } from '../types/auth';

// design-api.md §5; kontrak lengkap di docs/02. design/auth-api-integration.md (BE-06.1).

/** Role kanonik backend (INSTRUCTOR/STUDENT/ADMIN) → ROLE aplikasi (DOSEN/MAHASISWA/ADMIN). */
export function toUiRole(role) {
  return ROLE_FROM_BACKEND[role] ?? null;
}

export async function login(username, password, { isCurrent = () => true } = {}) {
  const data = await api.post('/auth/login', { username, password });
  if (isCurrent()) setToken(data.access_token);
  return data;
}

export function getCurrentUser() {
  return api.get('/auth/me');
}

export function hasToken() {
  return !!getToken();
}

// Backend tidak punya endpoint logout: token stateless cukup dihapus di client (§5).
export function logout() {
  setToken(null);
}
