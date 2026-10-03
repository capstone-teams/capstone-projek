import { api, setToken } from './apiClient';

// design-api.md §5; real Backend expects email in the field named "username".
export async function login(username, password) {
  const data = await api.post('/auth/login', { username, password });
  return data;
}

export function getCurrentUser() {
  return api.get('/auth/me');
}

export function logout() {
  setToken(null);
}
