import { api, getToken, setToken } from './apiClient';

// design-api.md §5; kontrak lengkap di docs/02. design/auth-api-integration.md (BE-06.1).

// Role kanonik backend (huruf besar) → role yang dipakai UI.
const UI_ROLES = { INSTRUCTOR: 'dosen', STUDENT: 'mahasiswa', ADMIN: 'admin' };

export function toUiRole(role) {
  return UI_ROLES[role] ?? null;
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
