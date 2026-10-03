import { act, useLayoutEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { AuthProvider } from '../src/context/AuthProvider';
import { useAuth } from '../src/hooks/useAuth';
import * as authService from '../src/services/authService';
import { getToken, setToken, request } from '../src/services/apiClient';
import { configureMock } from '../src/services/mock/mockServer';

vi.mock('../src/services/authService', () => ({
  login: vi.fn(), getCurrentUser: vi.fn(), logout: vi.fn(),
}));

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, host, auth;
function Probe() {
  const state = useAuth();
  useLayoutEffect(() => { auth = state; }, [state]);
  return <span>{state.initializing ? 'loading' : state.user?.name ?? 'anonymous'}</span>;
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function mount() {
  host = document.createElement('div');
  document.body.append(host);
  root = createRoot(host);
  await act(async () => { root.render(<AuthProvider><Probe /></AuthProvider>); });
}
beforeEach(() => {
  vi.resetAllMocks();
  setToken(null);
  configureMock({ latencyMs: 0 });
  authService.logout.mockImplementation(() => setToken(null));
});
afterEach(async () => {
  if (root) await act(async () => root.unmount());
  root = null;
  host?.remove();
  setToken(null);
});

test('anonymous startup never calls /auth/me', async () => {
  await mount();
  expect(auth.user).toBeNull();
  expect(auth.initializing).toBe(false);
  expect(authService.getCurrentUser).not.toHaveBeenCalled();
});
test('restores backend identity and maps firstname/lastname and instructor role', async () => {
  setToken('existing');
  authService.getCurrentUser.mockResolvedValue({ id: '1', firstname: 'Chandra', lastname: 'Utomo', role: 'instructor' });
  await mount();
  expect(auth.user).toMatchObject({ name: 'Chandra Utomo', role: 'dosen' });
  expect(auth.initializing).toBe(false);
});
test('invalid stored session is cleared', async () => {
  setToken('invalid');
  authService.getCurrentUser.mockRejectedValue(new Error('expired'));
  await mount();
  expect(auth.user).toBeNull();
  expect(getToken()).toBeNull();
});
test('login validates current user before exposing the session', async () => {
  await mount();
  authService.login.mockResolvedValue({ access_token: 'valid' });
  authService.getCurrentUser.mockResolvedValue({ id: '2', name: 'Noel', role: 'student' });
  let user;
  await act(async () => { user = await auth.login(' mahasiswa ', 'mahasiswa123'); });
  expect(authService.login).toHaveBeenCalledWith('mahasiswa', 'mahasiswa123');
  expect(user.role).toBe('mahasiswa');
  expect(auth.user).toEqual(user);
  expect(getToken()).toBe('valid');
});
test('failed /auth/me after login clears the newly issued token', async () => {
  await mount();
  authService.login.mockResolvedValue({ access_token: 'unusable' });
  authService.getCurrentUser.mockRejectedValue(new Error('expired'));
  await act(async () => { await expect(auth.login('dosen', 'dosen123')).rejects.toThrow('expired'); });
  expect(auth.user).toBeNull();
  expect(getToken()).toBeNull();
});
test('late startup response cannot restore a logged-out account', async () => {
  const restore = deferred();
  setToken('old');
  authService.getCurrentUser.mockReturnValue(restore.promise);
  await mount();
  await act(async () => { auth.logout(); restore.resolve({ id: '1', name: 'Old user', role: 'instructor' }); });
  expect(auth.user).toBeNull();
  expect(getToken()).toBeNull();
});
test('late login response cannot reauthenticate after logout', async () => {
  const login = deferred();
  await mount();
  authService.login.mockReturnValue(login.promise);
  const attempt = auth.login('dosen', 'dosen123');
  const rejected = expect(attempt).rejects.toThrow('dibatalkan');
  await act(async () => { auth.logout(); login.resolve({ access_token: 'late' }); await rejected; });
  expect(getToken()).toBeNull();
  expect(auth.user).toBeNull();
  expect(authService.getCurrentUser).not.toHaveBeenCalled();
});
test('401 from an authenticated API request signs the session out', async () => {
  await mount();
  authService.login.mockResolvedValue({ access_token: 'invalid-for-api' });
  authService.getCurrentUser.mockResolvedValue({ id: '1', name: 'Teacher', role: 'instructor' });
  await act(async () => { await auth.login('dosen', 'dosen123'); });
  await act(async () => { await expect(request('GET', '/auth/me')).rejects.toMatchObject({ status: 401 }); });
  expect(auth.user).toBeNull();
  expect(getToken()).toBeNull();
});
