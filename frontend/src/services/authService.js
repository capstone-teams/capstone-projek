import { api, setToken } from './apiClient';

// design-api.md §5
export async function login(username, password) {
  const data = await api.post('/auth/login', { username, password });
  setToken(data.access_token);
  return data;
}

export function getCurrentUser() {
  return api.get('/auth/me');
}

export function logout() {
  setToken(null);
}
