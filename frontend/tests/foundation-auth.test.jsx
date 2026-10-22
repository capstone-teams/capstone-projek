import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '../src/context/AuthProvider';
import { useAuth } from '../src/hooks/useAuth';
import { ApiError, request } from '../src/services/apiClient';
import { MOODLE_SESSION_KEY, TOKEN_STORAGE_KEY } from '../src/services/config';
import { AUTH_STATUS, ROLE_FROM_BACKEND, SESSION_NOTICE } from '../src/types/auth';

const service = vi.hoisted(() => ({
  requestToken: vi.fn(), resolveSession: vi.fn(), setMoodleToken: vi.fn(), onMoodleTokenInvalid: vi.fn(),
  login: vi.fn(), logout: vi.fn(), getCurrentUser: vi.fn(), hasToken: vi.fn(), toUiRole: vi.fn(),
}));
// apiClient asli dipakai (ApiError/request); onUnauthorized dibungkus spy agar registrasi handler dapat diperiksa.
const apiClient = vi.hoisted(() => ({ onUnauthorized: vi.fn(), actual: null }));
vi.mock('../src/services/moodle/moodleClient', () => service);
vi.mock('../src/services/moodle/moodleApi', () => service);
vi.mock('../src/services/authService', () => service);
vi.mock('../src/services/apiClient', async (importOriginal) => {
  apiClient.actual = await importOriginal();
  return { ...apiClient.actual, onUnauthorized: apiClient.onUnauthorized };
});
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const teacher = { user: { id: 3, username: 'dosen', fullname: 'Rina Kartika', teacherCourseIds: [2] }, site: { name: 'Moodle ITK' } };
const student = { user: { id: 5, username: 'mahasiswa', fullname: 'Andi Saputra', teacherCourseIds: [] }, site: teacher.site };
const instructorMe = { id: 'user_001', username: 'dosen', firstname: 'Rina', lastname: 'Kartika', email: 'dosen@lecturer.itk.ac.id', role: 'INSTRUCTOR' };
const studentMe = { id: 'user_002', username: 'mahasiswa', firstname: 'Andi', lastname: 'Saputra', email: 'mahasiswa@student.itk.ac.id', role: 'STUDENT' };
const authFailed = () => new ApiError(401, 'AUTHENTICATION_FAILED', 'Autentikasi gagal.');

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const storedTokens = () => [localStorage.getItem(TOKEN_STORAGE_KEY), localStorage.getItem(MOODLE_SESSION_KEY)];
function storeSession(moodle = 'mock-3-test', backend = 'mock-token:user_001') {
  if (moodle) localStorage.setItem(MOODLE_SESSION_KEY, JSON.stringify({ token: moodle }));
  if (backend) localStorage.setItem(TOKEN_STORAGE_KEY, backend);
}

let node, root, state;
function Probe() { state = useAuth(); return <span>{state.user?.fullname ?? 'anonymous'}</span>; }
async function mount() {
  root = createRoot(node);
  await act(async () => root.render(<AuthProvider><Probe /></AuthProvider>));
}
beforeEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
  // Token backend disimpan seperti authService asli supaya hasToken/logout konsisten.
  service.hasToken.mockImplementation(() => !!localStorage.getItem(TOKEN_STORAGE_KEY));
  service.logout.mockImplementation(() => localStorage.removeItem(TOKEN_STORAGE_KEY));
  service.login.mockImplementation(async (username) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, `mock-token:${username}`);
    return { access_token: `mock-token:${username}`, token_type: 'bearer', user: {} };
  });
  apiClient.onUnauthorized.mockImplementation((handler) => apiClient.actual.onUnauthorized(handler));
  service.toUiRole.mockImplementation((role) => ROLE_FROM_BACKEND[role] ?? null);
  node = document.createElement('div');
  document.body.appendChild(node);
});
afterEach(async () => {
  await act(async () => root?.unmount());
  root = null;
  node.remove();
});

describe('FE-06.2 login', () => {
  it('logs in through the backend first, then Moodle with the backend username', async () => {
    service.getCurrentUser.mockResolvedValueOnce(instructorMe);
    service.requestToken.mockResolvedValueOnce('mock-3-new');
    service.resolveSession.mockResolvedValueOnce(teacher);
    await mount();
    await act(async () => state.login('dosen@lecturer.itk.ac.id', 'dosen123'));
    expect(service.login).toHaveBeenCalledWith('dosen@lecturer.itk.ac.id', 'dosen123', expect.any(Object));
    expect(service.requestToken).toHaveBeenCalledWith('dosen', 'dosen123');
    expect(service.login.mock.invocationCallOrder[0]).toBeLessThan(service.requestToken.mock.invocationCallOrder[0]);
    expect(state.user).toMatchObject({ id: 3, fullname: 'Rina Kartika', role: 'DOSEN', backendId: 'user_001', teacherCourseIds: [2] });
    expect(storedTokens()).toEqual(['mock-token:dosen@lecturer.itk.ac.id', JSON.stringify({ token: 'mock-3-new' })]);
  });

  it('takes the role from the backend, not from Moodle course permissions', async () => {
    service.getCurrentUser.mockResolvedValueOnce(studentMe);
    service.requestToken.mockResolvedValueOnce('mock-3-new');
    service.resolveSession.mockResolvedValueOnce(teacher);
    await mount();
    await act(async () => state.login('mahasiswa', 'mahasiswa123'));
    expect(state.user.role).toBe('MAHASISWA');
  });

  it('rejects with the backend error and never contacts Moodle when credentials are wrong', async () => {
    service.login.mockRejectedValueOnce(authFailed());
    await mount();
    const error = await act(async () => state.login('dosen', 'salah').catch((e) => e));
    expect(error).toMatchObject({ code: 'AUTHENTICATION_FAILED', message: 'Autentikasi gagal.' });
    expect(service.requestToken).not.toHaveBeenCalled();
    expect(state.user).toBeNull();
    expect(storedTokens()).toEqual([null, null]);
  });

  it('rolls back the backend token when the Moodle step fails', async () => {
    service.getCurrentUser.mockResolvedValueOnce(instructorMe);
    service.requestToken.mockRejectedValueOnce(Object.assign(new Error('Invalid login'), { code: 'invalidlogin' }));
    await mount();
    const error = await act(async () => state.login('dosen', 'dosen123').catch((e) => e));
    expect(error).toMatchObject({ code: 'invalidlogin', source: 'moodle' });
    expect(state.user).toBeNull();
    expect(storedTokens()).toEqual([null, null]);
  });

  it('a pending login cannot store credentials after logout', async () => {
    const pending = deferred();
    service.getCurrentUser.mockReturnValueOnce(pending.promise);
    await mount();
    let result;
    await act(async () => { result = state.login('dosen', 'dosen123').catch((error) => error); });
    await act(async () => state.logout());
    await act(async () => { pending.resolve(instructorMe); await result; });
    expect(state.user).toBeNull();
    expect(service.requestToken).not.toHaveBeenCalled();
    expect(localStorage.getItem(MOODLE_SESSION_KEY)).toBeNull();
  });
});

describe('FE-06.2 session restore', () => {
  it('restores the user from GET /auth/me and Moodle before ending initialization', async () => {
    const pending = deferred();
    storeSession();
    service.getCurrentUser.mockReturnValueOnce(pending.promise);
    service.resolveSession.mockResolvedValueOnce(teacher);
    await mount();
    expect(state.initializing).toBe(true);
    expect(state.user).toBeNull();
    await act(async () => pending.resolve(instructorMe));
    expect(state.initializing).toBe(false);
    expect(state.user).toMatchObject({ fullname: 'Rina Kartika', role: 'DOSEN', backendId: 'user_001' });
    expect(storedTokens()).toEqual(['mock-token:user_001', JSON.stringify({ token: 'mock-3-test' })]);
  });

  it('expires the session when the backend rejects the stored token', async () => {
    storeSession();
    service.getCurrentUser.mockRejectedValueOnce(authFailed());
    service.resolveSession.mockResolvedValueOnce(teacher);
    await mount();
    expect(state.user).toBeNull();
    expect(state.initializing).toBe(false);
    expect(state.sessionNotice).toBe(SESSION_NOTICE.EXPIRED);
    expect(storedTokens()).toEqual([null, null]);
  });

  it('discards a rejected Moodle token', async () => {
    storeSession('expired');
    service.getCurrentUser.mockResolvedValueOnce(instructorMe);
    service.resolveSession.mockRejectedValueOnce(new Error('invalidtoken'));
    await mount();
    expect(state.user).toBeNull();
    expect(storedTokens()).toEqual([null, null]);
  });

  it('keeps the tokens when the backend is unreachable during restore', async () => {
    storeSession();
    service.getCurrentUser.mockRejectedValueOnce(new ApiError(0, 'NETWORK_ERROR', 'Tidak dapat terhubung ke server backend.'));
    service.resolveSession.mockResolvedValueOnce(teacher);
    await mount();
    expect(state.user).toBeNull();
    expect(state.initializing).toBe(false);
    expect(state.sessionNotice).toBe(SESSION_NOTICE.UNAVAILABLE);
    expect(storedTokens()).toEqual(['mock-token:user_001', JSON.stringify({ token: 'mock-3-test' })]);
  });

  it('clears an incomplete session without restoring it', async () => {
    storeSession('mock-3-test', null);
    await mount();
    expect(state.initializing).toBe(false);
    expect(service.getCurrentUser).not.toHaveBeenCalled();
    expect(service.resolveSession).not.toHaveBeenCalled();
    expect(storedTokens()).toEqual([null, null]);
  });

  it('ignores malformed session storage', async () => {
    localStorage.setItem(MOODLE_SESSION_KEY, '{broken');
    await mount();
    expect(state.initializing).toBe(false);
    expect(state.user).toBeNull();
    expect(service.resolveSession).not.toHaveBeenCalled();
  });

  it('a late session restoration cannot undo logout', async () => {
    const pending = deferred();
    storeSession();
    service.getCurrentUser.mockResolvedValueOnce(instructorMe);
    service.resolveSession.mockReturnValueOnce(pending.promise);
    await mount();
    await act(async () => state.logout());
    await act(async () => pending.resolve(teacher));
    expect(state.user).toBeNull();
    expect(state.initializing).toBe(false);
    expect(storedTokens()).toEqual([null, null]);
  });

  it('a late restore error cannot clear a newer successful login', async () => {
    const pending = deferred();
    storeSession('old', 'old-backend');
    service.getCurrentUser.mockReturnValueOnce(pending.promise).mockResolvedValueOnce(studentMe);
    service.resolveSession.mockResolvedValue(student);
    service.requestToken.mockResolvedValueOnce('mock-5-new');
    await mount();
    await act(async () => state.login('mahasiswa', 'mahasiswa123'));
    await act(async () => pending.reject(authFailed()));
    expect(state.user).toMatchObject({ fullname: 'Andi Saputra', role: 'MAHASISWA' });
    expect(JSON.parse(localStorage.getItem(MOODLE_SESSION_KEY)).token).toBe('mock-5-new');
  });
});

describe('FE-06.2 logout & expiry', () => {
  async function loggedIn() {
    service.getCurrentUser.mockResolvedValueOnce(instructorMe);
    service.requestToken.mockResolvedValueOnce('mock-3-new');
    service.resolveSession.mockResolvedValueOnce(teacher);
    await mount();
    await act(async () => state.login('dosen', 'dosen123'));
  }

  it('logout removes the token and the user from state', async () => {
    await loggedIn();
    await act(async () => state.logout());
    expect(state).toMatchObject({ user: null, isAuthenticated: false, sessionNotice: null });
    expect(service.setMoodleToken).toHaveBeenLastCalledWith(null);
    expect(storedTokens()).toEqual([null, null]);
  });

  it('a 401 for the stored token on a later request expires the session', async () => {
    await loggedIn();
    // Mode mock: token "mock-token:dosen" tidak dikenal mock backend → 401.
    await act(async () => { await request('GET', '/courses').catch(() => {}); });
    expect(state.user).toBeNull();
    expect(state.sessionNotice).toBe(SESSION_NOTICE.EXPIRED);
    expect(storedTokens()).toEqual([null, null]);
  });

  it('triggers expire, clears session, and notifies SESSION_NOTICE.EXPIRED when unauthorized (401) occurs', async () => {
    storeSession();
    service.getCurrentUser.mockResolvedValueOnce(instructorMe);
    service.resolveSession.mockResolvedValueOnce(teacher);
    await mount();
    expect(state.user).toMatchObject(teacher.user);
    expect(state.isAuthenticated).toBe(true);
    expect(state.sessionNotice).toBeNull();

    const onExpire = apiClient.onUnauthorized.mock.calls.find(
      (call) => typeof call[0] === 'function',
    )?.[0];
    expect(onExpire).toBeDefined();

    await act(async () => {
      onExpire();
    });

    expect(state.user).toBeNull();
    expect(state.status).toBe(AUTH_STATUS.ANONYMOUS);
    expect(state.isAuthenticated).toBe(false);
    expect(state.sessionNotice).toBe(SESSION_NOTICE.EXPIRED);
    expect(storedTokens()).toEqual([null, null]);
    expect(service.logout).toHaveBeenCalled();
  });

  it('unregisters onUnauthorized handler on unmount', async () => {
    await mount();
    expect(apiClient.onUnauthorized).toHaveBeenCalledWith(expect.any(Function));
    await act(async () => root?.unmount());
    root = null;
    expect(apiClient.onUnauthorized).toHaveBeenLastCalledWith(null);
  });
});
