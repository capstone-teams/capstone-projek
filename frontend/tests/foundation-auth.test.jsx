import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '../src/context/AuthProvider';
import { useAuth } from '../src/hooks/useAuth';
import { MOODLE_SESSION_KEY } from '../src/services/config';

const service = vi.hoisted(() => ({
  requestToken: vi.fn(), resolveSession: vi.fn(), setMoodleToken: vi.fn(),
  onMoodleTokenInvalid: vi.fn(), login: vi.fn(), logout: vi.fn(),
}));
vi.mock('../src/services/moodle/moodleClient', () => service);
vi.mock('../src/services/moodle/moodleApi', () => service);
vi.mock('../src/services/authService', () => service);
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const teacher = { user: { id: 3, fullname: 'Rina Kartika', role: 'dosen' }, site: { name: 'Moodle ITK' } };
const student = { user: { id: 5, fullname: 'Andi Saputra', role: 'mahasiswa' }, site: teacher.site };
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
let node, root, state;
function Probe() { state = useAuth(); return <span>{state.user?.fullname ?? 'anonymous'}</span>; }
async function mount() {
  root = createRoot(node);
  await act(async () => root.render(<AuthProvider><Probe /></AuthProvider>));
}
beforeEach(() => {
  vi.resetAllMocks();
  service.login.mockResolvedValue({});
  localStorage.clear();
  node = document.createElement('div');
  document.body.appendChild(node);
});
afterEach(async () => {
  await act(async () => root?.unmount());
  root = null;
  node.remove();
});

describe('FE-04.1 session lifecycle', () => {
  it('restores the Moodle user before ending initialization', async () => {
    const pending = deferred();
    localStorage.setItem(MOODLE_SESSION_KEY, JSON.stringify({ token: 'mock-3-test' }));
    service.resolveSession.mockReturnValueOnce(pending.promise);
    await mount();
    expect(state.initializing).toBe(true);
    expect(state.user).toBeNull();
    await act(async () => pending.resolve(teacher));
    expect(state.initializing).toBe(false);
    expect(state.user).toEqual(teacher.user);
  });

  it('discards invalid stored credentials', async () => {
    localStorage.setItem(MOODLE_SESSION_KEY, JSON.stringify({ token: 'expired' }));
    service.resolveSession.mockRejectedValueOnce(new Error('invalidtoken'));
    await mount();
    expect(state.user).toBeNull();
    expect(state.initializing).toBe(false);
    expect(localStorage.getItem(MOODLE_SESSION_KEY)).toBeNull();
    expect(service.logout).toHaveBeenCalled();
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
    localStorage.setItem(MOODLE_SESSION_KEY, JSON.stringify({ token: 'mock-3-test' }));
    service.resolveSession.mockReturnValueOnce(pending.promise);
    await mount();
    await act(async () => state.logout());
    await act(async () => pending.resolve(teacher));
    expect(state.user).toBeNull();
    expect(state.initializing).toBe(false);
    expect(localStorage.getItem(MOODLE_SESSION_KEY)).toBeNull();
  });

  it('a pending login cannot store credentials after logout', async () => {
    const pending = deferred();
    service.requestToken.mockReturnValueOnce(pending.promise);
    service.resolveSession.mockResolvedValueOnce(teacher);
    await mount();
    let result;
    await act(async () => { result = state.login('dosen', 'dosen123').catch((error) => error); });
    await act(async () => state.logout());
    await act(async () => { pending.resolve('mock-3-late'); await result; });
    expect(state.user).toBeNull();
    expect(localStorage.getItem(MOODLE_SESSION_KEY)).toBeNull();
    expect(service.login).not.toHaveBeenCalled();
  });

  it('a late restore error cannot clear a newer successful login', async () => {
    const pending = deferred();
    localStorage.setItem(MOODLE_SESSION_KEY, JSON.stringify({ token: 'old' }));
    service.resolveSession.mockReturnValueOnce(pending.promise).mockResolvedValueOnce(student);
    service.requestToken.mockResolvedValueOnce('mock-5-new');
    await mount();
    await act(async () => state.login('mahasiswa', 'mahasiswa123'));
    await act(async () => pending.reject(new Error('expired old token')));
    expect(state.user).toEqual(student.user);
    expect(JSON.parse(localStorage.getItem(MOODLE_SESSION_KEY)).token).toBe('mock-5-new');
  });

  it('Moodle access survives a separate backend login failure', async () => {
    service.requestToken.mockResolvedValueOnce('mock-3-test');
    service.resolveSession.mockResolvedValueOnce(teacher);
    service.login.mockRejectedValueOnce(new Error('backend unavailable'));
    await mount();
    await act(async () => state.login('dosen', 'dosen123'));
    expect(state.user).toEqual(teacher.user);
    expect(JSON.parse(localStorage.getItem(MOODLE_SESSION_KEY)).token).toBe('mock-3-test');
  });
});
