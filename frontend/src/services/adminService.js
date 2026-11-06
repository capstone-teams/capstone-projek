import { api } from './apiClient';

// Administrasi pengguna (GET /api/v1/admin/users..., khusus peran ADMIN).

/** GET /admin/users: [{ id, username, firstname, lastname, email, role, status, created_at }]. */
export function listUsers() {
  return api.get('/admin/users').then((data) => data?.users ?? []);
}

/** GET /admin/users/{id} */
export function getUser(userId) {
  return api.get(`/admin/users/${userId}`);
}
