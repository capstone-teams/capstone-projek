import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthContext } from '../src/context/authContext';
import { AuthProvider } from '../src/context/AuthProvider';
import { AppStateProvider } from '../src/context/AppStateProvider';
import { useAuth } from '../src/hooks/useAuth';
import { useAppState, usePreference } from '../src/hooks/useAppState';
import { useCurrentUser } from '../src/hooks/useCurrentUser';
import { useAction } from '../src/hooks/useApi';
import { appStateReducer, initialAppState, MAX_NOTIFICATIONS, preferencesKey } from '../src/state/appState';
import { readJson, writeJson } from '../src/utils/storage';
import { MOODLE_SESSION_KEY, TOKEN_STORAGE_KEY } from '../src/services/config';
import { ApiError } from '../src/services/apiClient';
import { AUTH_STATUS, ROLE_FROM_BACKEND, SESSION_NOTICE } from '../src/types/auth';
import AppStatus from '../src/components/layout/AppStatus';
import MyCoursesPage from '../src/pages/moodle/MyCoursesPage';
import LoginPage from '../src/pages/auth/LoginPage';

const service = vi.hoisted(() => ({
  requestToken: vi.fn(), resolveSession: vi.fn(), setMoodleToken: vi.fn(), onMoodleTokenInvalid: vi.fn(),
  login: vi.fn(), logout: vi.fn(), getCurrentUser: vi.fn(), hasToken: vi.fn(), toUiRole: vi.fn(), getCoursesByClassification: vi.fn(),
}));
vi.mock('../src/services/moodle/moodleClient', () => service);
vi.mock('../src/services/moodle/moodleApi', () => service);
vi.mock('../src/services/authService', () => service);
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const teacher = { id: 3, fullname: 'Rina Kartika', username: 'dosen', role: 'DOSEN', teacherCourseIds: [2] };
const student = { id: 5, fullname: 'Andi Saputra', username: 'mahasiswa', role: 'MAHASISWA', teacherCourseIds: [] };
const studentMe = { id: 'user_002', username: 'mahasiswa', firstname: 'Andi', lastname: 'Saputra', email: 'mahasiswa@student.itk.ac.id', role: 'STUDENT' };
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

let node, root, app, auth, current;
async function render(element) {
  root ??= createRoot(node);
  await act(async () => root.render(<MemoryRouter>{element}</MemoryRouter>));
}
function withSession(element, value) {
  return <AuthContext.Provider value={value}><AppStateProvider>{element}</AppStateProvider></AuthContext.Provider>;
}
function AppProbe() { app = useAppState(); current = useCurrentUser(); return null; }
function AuthProbe() { auth = useAuth(); return <span>{auth.status}</span>; }

beforeEach(() => {
  vi.resetAllMocks();
  service.login.mockResolvedValue({});
  service.hasToken.mockImplementation(() => !!localStorage.getItem(TOKEN_STORAGE_KEY));
  service.logout.mockImplementation(() => localStorage.removeItem(TOKEN_STORAGE_KEY));
  service.toUiRole.mockImplementation((role) => ROLE_FROM_BACKEND[role] ?? null);
  localStorage.clear();
  node = document.createElement('div');
  document.body.appendChild(node);
});
afterEach(async () => {
  await act(async () => root?.unmount());
  root = null;
  node.remove();
  vi.restoreAllMocks();
});

describe('FE state: storage', () => {
  it('returns the fallback for corrupt JSON and survives unavailable storage', () => {
    localStorage.setItem('k', '{broken');
    expect(readJson('k', 'fallback')).toBe('fallback');
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('QuotaExceeded'); });
    expect(writeJson('k', { a: 1 })).toBe(false);
  });
});

describe('FE state: reducer', () => {
  it('drops transient state when the session changes', () => {
    const busy = { ...initialAppState, userId: 3, loading: [{ id: 1 }], errors: [{ id: 2 }], notifications: [{ id: 3 }] };
    expect(appStateReducer(busy, { type: 'session/changed', userId: 5, preferences: { a: 1 } }))
      .toEqual({ ...initialAppState, userId: 5, preferences: { a: 1 } });
  });

  it('keeps one error per source, caps notifications and ignores no-op dismissals', () => {
    let state = appStateReducer(initialAppState, { type: 'error/report', error: { id: 1, source: 'x', message: 'old' } });
    state = appStateReducer(state, { type: 'error/report', error: { id: 2, source: 'x', message: 'new' } });
    expect(state.errors.map((e) => e.message)).toEqual(['new']);
    expect(appStateReducer(state, { type: 'error/dismiss', id: 99 })).toBe(state);
    for (let id = 1; id <= MAX_NOTIFICATIONS + 2; id += 1) {
      state = appStateReducer(state, { type: 'notification/push', notification: { id } });
    }
    expect(state.notifications.map((n) => n.id)).toEqual([3, 4, 5]);
  });
});

describe('FE state: authentication and current user', () => {
  it('moves anonymous → authenticated → anonymous and exposes the user', async () => {
    service.getCurrentUser.mockResolvedValueOnce(studentMe);
    service.requestToken.mockResolvedValueOnce('token');
    service.resolveSession.mockResolvedValueOnce({ user: student, site: { name: 'Moodle ITK' } });
    await render(<AuthProvider><AuthProbe /></AuthProvider>);
    expect(auth.status).toBe(AUTH_STATUS.ANONYMOUS);
    await act(async () => auth.login('mahasiswa', 'x'));
    expect(auth).toMatchObject({ status: AUTH_STATUS.AUTHENTICATED, isAuthenticated: true, user: student });
    await act(async () => auth.logout());
    expect(auth).toMatchObject({ status: AUTH_STATUS.ANONYMOUS, isAuthenticated: false, user: null, sessionNotice: null });
  });

  it('marks the session as expired when the stored token is rejected', async () => {
    localStorage.setItem(MOODLE_SESSION_KEY, JSON.stringify({ token: 'expired' }));
    localStorage.setItem(TOKEN_STORAGE_KEY, 'expired-backend');
    service.getCurrentUser.mockRejectedValueOnce(new ApiError(401, 'AUTHENTICATION_FAILED', 'Autentikasi gagal.'));
    service.resolveSession.mockRejectedValueOnce(new Error('invalidtoken'));
    await render(<AuthProvider><AuthProbe /></AuthProvider>);
    expect(auth.status).toBe(AUTH_STATUS.ANONYMOUS);
    expect(auth.sessionNotice).toBe(SESSION_NOTICE.EXPIRED);
    expect(localStorage.getItem(MOODLE_SESSION_KEY)).toBeNull();
  });

  it('shows the expired-session notice on the login page', async () => {
    await render(<AuthContext.Provider value={{ user: null, sessionNotice: SESSION_NOTICE.EXPIRED }}><LoginPage /></AuthContext.Provider>);
    expect(node.textContent).toContain('Sesi Anda telah berakhir');
  });

  async function submitLogin(username, password) {
    const setValue = (input, value) => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value);
      input.dispatchEvent(new Event('input', { bubbles: true }));
    };
    await act(async () => {
      setValue(node.querySelector('#username'), username);
      setValue(node.querySelector('#password'), password);
    });
    await act(async () => node.querySelector('form').requestSubmit());
  }

  it('shows the backend error message on the login form and stays anonymous', async () => {
    service.login.mockRejectedValueOnce(new ApiError(401, 'AUTHENTICATION_FAILED', 'Autentikasi gagal.'));
    await render(<AuthProvider><AuthProbe /><LoginPage /></AuthProvider>);
    await submitLogin('dosen', 'salah');
    const alert = node.querySelector('[role="alert"]');
    expect(alert.textContent).toContain('Login gagal');
    expect(alert.textContent).toContain('Autentikasi gagal.');
    expect(auth.isAuthenticated).toBe(false);
    expect(service.requestToken).not.toHaveBeenCalled();
    expect(node.querySelector('button[type="submit"]').disabled).toBe(false);
  });

  it('succeeds login through backend even if Moodle connection fails', async () => {
    service.getCurrentUser.mockResolvedValueOnce(studentMe);
    service.requestToken.mockRejectedValueOnce(Object.assign(new Error('Invalid login, please try again'), { code: 'invalidlogin' }));
    await render(<AuthProvider><AuthProbe /><LoginPage /></AuthProvider>);
    await submitLogin('mahasiswa', 'mahasiswa123');
    expect(auth.isAuthenticated).toBe(true);
    expect(auth.user).toMatchObject({ username: 'mahasiswa', role: 'MAHASISWA' });
  });

  it('locks the login form while the request is pending', async () => {
    const pending = deferred();
    service.login.mockReturnValueOnce(pending.promise);
    await render(<AuthProvider><LoginPage /></AuthProvider>);
    await submitLogin('dosen', 'dosen123');
    const button = node.querySelector('button[type="submit"]');
    expect(button.disabled).toBe(true);
    expect(button.textContent).toBe('Memproses…');
    expect(node.querySelector('form').getAttribute('aria-busy')).toBe('true');
    expect(node.querySelector('#username').readOnly).toBe(true);
    expect(node.querySelector('#password').readOnly).toBe(true);
    await act(async () => pending.reject(new ApiError(0, 'NETWORK_ERROR', 'Tidak dapat terhubung ke server backend.')));
    expect(button.disabled).toBe(false);
    expect(node.querySelector('[role="alert"]').textContent).toContain('Tidak dapat terhubung ke server backend.');
  });

  it('shows a restore-unavailable notice on the login page', async () => {
    await render(<AuthContext.Provider value={{ user: null, sessionNotice: SESSION_NOTICE.UNAVAILABLE }}><LoginPage /></AuthContext.Provider>);
    expect(node.textContent).toContain('Sesi belum dapat dipulihkan');
  });

  it('derives role helpers from the current user', async () => {
    await render(withSession(<AppProbe />, { user: teacher }));
    expect(current).toMatchObject({ role: 'DOSEN', isDosen: true, isMahasiswa: false });
    expect(current.isTeacherOf('2')).toBe(true);
    expect(current.isTeacherOf(7)).toBe(false);
  });
});

describe('FE state: application UI state and persistence', () => {
  function Pref() { const [value, setValue] = usePreference('demo', 'default'); app = { value, setValue }; return <span>{value}</span>; }

  it('persists preferences per user and isolates them between users', async () => {
    await render(withSession(<Pref />, { user: teacher }));
    await act(async () => app.setValue('teacher-choice'));
    expect(readJson(preferencesKey(teacher.id))).toEqual({ demo: 'teacher-choice' });
    await render(withSession(<Pref />, { user: student }));
    expect(node.textContent).toBe('default');
    await render(withSession(<Pref />, { user: teacher }));
    expect(node.textContent).toBe('teacher-choice');
  });

  it('falls back to component state without a provider', async () => {
    await render(<Pref />);
    await act(async () => app.setValue('local'));
    expect(node.textContent).toBe('local');
    expect(localStorage.length).toBe(0);
  });

  it('remembers the course filter across visits', async () => {
    localStorage.setItem(preferencesKey(teacher.id), JSON.stringify({ 'myCourses.classification': 'past' }));
    service.getCoursesByClassification.mockResolvedValue([]);
    await render(withSession(<MyCoursesPage />, { user: teacher }));
    expect(service.getCoursesByClassification).toHaveBeenLastCalledWith('past');
    expect(node.querySelector('select').value).toBe('past');
  });

  it('ignores an unknown stored course filter', async () => {
    localStorage.setItem(preferencesKey(teacher.id), JSON.stringify({ 'myCourses.classification': 'hacked' }));
    service.getCoursesByClassification.mockResolvedValue([]);
    await render(withSession(<MyCoursesPage />, { user: teacher }));
    expect(service.getCoursesByClassification).toHaveBeenLastCalledWith('all');
  });

  it('shows and dismisses notifications', async () => {
    await render(withSession(<><AppProbe /><AppStatus /></>, { user: teacher }));
    await act(async () => app.notify('Rencana disimpan.', { type: 'success' }));
    expect(node.textContent).toContain('Rencana disimpan.');
    await act(async () => node.querySelector('[aria-label="Tutup notifikasi"]').click());
    expect(app.notifications).toEqual([]);
  });
});

describe('FE state: shared loading and error', () => {
  function Act({ action }) { const a = useAction(action, { loadingLabel: 'Menyimpan…' }); app = { ...useAppState(), action: a }; return <AppStatus />; }

  it('tracks a labelled action globally until it settles, even on failure', async () => {
    const pending = deferred();
    await render(withSession(<Act action={() => pending.promise} />, { user: teacher }));
    let result;
    await act(async () => { result = app.action.run().catch((e) => e); });
    expect(app.isLoading).toBe(true);
    expect(node.querySelector('[role="progressbar"]').getAttribute('aria-label')).toBe('Menyimpan…');
    await act(async () => { pending.reject(new Error('gagal')); await result; });
    expect(app.isLoading).toBe(false);
    expect(node.querySelector('[role="progressbar"]')).toBeNull();
  });

  it('counts overlapping tasks and stops each only once', async () => {
    await render(withSession(<AppProbe />, { user: teacher }));
    let stopA, stopB;
    await act(async () => { stopA = app.startLoading('A'); stopB = app.startLoading('B'); });
    await act(async () => { stopA(); stopA(); });
    expect(app.loading.map((t) => t.label)).toEqual(['B']);
    await act(async () => stopB());
    expect(app.isLoading).toBe(false);
  });

  it('reports, dismisses and clears global errors; aborts are ignored', async () => {
    await render(withSession(<><AppProbe /><AppStatus /></>, { user: teacher }));
    await act(async () => {
      app.reportError(new DOMException('stale', 'AbortError'));
      app.reportError(new Error('Pertama'));
      app.reportError('Kedua', { title: 'Judul' });
    });
    expect(app.errors.map((e) => e.message)).toEqual(['Pertama', 'Kedua']);
    await act(async () => node.querySelector('[aria-label="Tutup"]').click());
    expect(app.errors.map((e) => e.message)).toEqual(['Kedua']);
    await act(async () => app.clearErrors());
    expect(node.querySelector('[role="alert"]')).toBeNull();
  });

  it('resets transient state when the user logs out', async () => {
    await render(withSession(<AppProbe />, { user: teacher }));
    await act(async () => { app.startLoading('x'); app.reportError(new Error('e')); app.notify('n'); });
    await render(withSession(<AppProbe />, { user: null }));
    expect(app).toMatchObject({ userId: null, loading: [], errors: [], notifications: [], preferences: {} });
  });
});
