import { api, getToken, setToken } from './apiClient';
import { ROLE_FROM_BACKEND } from '../types/auth';


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
