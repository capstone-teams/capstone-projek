// @vitest-environment node
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { api, getToken, setToken, onUnauthorized } from '../src/services/apiClient';
import * as authService from '../src/services/authService';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';

beforeEach(() => { resetMockDb(); configureMock({ latencyMs: 0 }); setToken(null); });
afterEach(() => { setToken(null); onUnauthorized(null); vi.unstubAllGlobals(); vi.doUnmock('../src/services/config.js'); });

test.each([
  ['dosen', 'dosen123', 'instructor'],
  ['mahasiswa', 'mahasiswa123', 'student'],
  ['chandra.cahyo@itk.ac.id', 'dosen123', 'instructor'],
])('mock login accepts the defined account %s', async (username, password, role) => {
  const session = await authService.login(username, password);
  expect(session.user.role).toBe(role);
  expect(getToken()).toBeNull(); // Only the provider commits a validated session.
  setToken(session.access_token);
  expect((await authService.getCurrentUser()).role).toBe(role);
});
test.each([['unknown', 'dosen123'], ['dosen', 'wrong'], ['dosen', ''], ['dosen-impersonation', 'dosen123']])(
  'mock login rejects invalid credentials %s/%s', async (username, password) => {
    await expect(authService.login(username, password)).rejects.toMatchObject({ status: 401 });
    expect(getToken()).toBeNull();
  },
);
test('mock server denies instructor operations for a student token', async () => {
  setToken('mock-token:user_002');
  await expect(api.get('/courses')).rejects.toMatchObject({ status: 403 });
});
test('an obsolete 401 cannot log out a newer token', async () => {
  configureMock({ latencyMs: 5 });
  const logout = vi.fn();
  onUnauthorized(logout);
  setToken('expired');
  const pending = api.get('/auth/me');
  setToken('mock-token:user_001');
  await expect(pending).rejects.toMatchObject({ status: 401 });
  expect(logout).not.toHaveBeenCalled();
});
test('real backend request preserves email identity, Bearer token, query and error mapping', async () => {
  vi.resetModules();
  vi.doMock('../src/services/config.js', () => ({ USE_MOCK: false, API_BASE_URL: 'http://localhost:8000/api/v1', TOKEN_STORAGE_KEY: 'agentic-lms.token' }));
  const fetcher = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'backend' }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ id: '1', role: 'instructor' }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ error: { code: 'AUTHENTICATION_FAILED', message: 'Expired' } }), { status: 401 }));
  vi.stubGlobal('fetch', fetcher);
  const real = await import('../src/services/apiClient.js');
  const logout = vi.fn();
  real.onUnauthorized(logout);
  await real.api.post('/auth/login', { username: 'dosen@itk.ac.id', password: 'secret' });
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ username: 'dosen@itk.ac.id', password: 'secret' });
  real.setToken('backend');
  await real.api.get('/auth/me', { query: { sample: 'a b' } });
  expect(fetcher.mock.calls[1][0]).toBe('http://localhost:8000/api/v1/auth/me?sample=a+b');
  expect(new Headers(fetcher.mock.calls[1][1].headers).get('Authorization')).toBe('Bearer backend');
  await expect(real.api.get('/auth/me')).rejects.toMatchObject({ status: 401, code: 'AUTHENTICATION_FAILED', message: 'Expired' });
  expect(logout).toHaveBeenCalledOnce();
  real.setToken(null);
  real.onUnauthorized(null);
});
