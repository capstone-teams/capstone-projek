import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAction, useApi } from '../src/hooks/useApi';
import { AuthContext } from '../src/context/authContext';
import MyCoursesPage from '../src/pages/moodle/MyCoursesPage';
import TeachingProfilePage from '../src/pages/ai/TeachingProfilePage';

const services = vi.hoisted(() => ({ getCoursesByClassification: vi.fn(), getProfile: vi.fn(), updateProfile: vi.fn() }));
vi.mock('../src/services/moodle/moodleApi', () => services);
vi.mock('../src/services/profileService', () => services);
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let node, root, state;
const user = { id: 3, fullname: 'Rina Kartika', username: 'dosen', teacherCourseIds: [2], role: 'dosen' };
const course = { id: 2, fullname: 'Pemrograman Web', shortname: 'IF2105' };
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function render(element) {
  root ??= createRoot(node);
  await act(async () => root.render(<MemoryRouter><AuthContext.Provider value={{ user }}>{element}</AuthContext.Provider></MemoryRouter>));
}
beforeEach(() => {
  vi.resetAllMocks();
  node = document.createElement('div');
  document.body.appendChild(node);
});
afterEach(async () => { await act(async () => root?.unmount()); root = null; node.remove(); });

function Resource({ fetcher, resource = 'one' }) { state = useApi(fetcher, [resource]); return <span>{state.loading ? 'loading' : state.error?.message ?? state.data}</span>; }
function Action({ action }) { state = useAction(action); return <span>{state.pending ? 'pending' : state.error?.message ?? 'ready'}</span>; }

describe('FE-04.1 shared request states', () => {
  it('loading becomes error and an explicit retry can succeed', async () => {
    const pending = deferred();
    const fetcher = vi.fn().mockReturnValueOnce(pending.promise).mockResolvedValueOnce('recovered');
    await render(<Resource fetcher={fetcher} />);
    expect(node.textContent).toBe('loading');
    await act(async () => pending.reject(new Error('unavailable')));
    expect(node.textContent).toBe('unavailable');
    await act(async () => state.reload());
    expect(node.textContent).toBe('recovered');
    expect(state.error).toBeNull();
  });

  it('late data from an earlier dependency cannot replace the latest result', async () => {
    const first = deferred();
    const fetcher = vi.fn().mockReturnValueOnce(first.promise).mockResolvedValueOnce('second');
    await render(<Resource fetcher={fetcher} />);
    await render(<Resource fetcher={fetcher} resource="two" />);
    await act(async () => first.resolve('obsolete'));
    expect(node.textContent).toBe('second');
  });

  it('an older failed reload cannot replace a newer successful reload', async () => {
    const pending = deferred();
    const fetcher = vi.fn().mockReturnValueOnce(pending.promise).mockResolvedValueOnce('current');
    await render(<Resource fetcher={fetcher} />);
    await act(async () => state.reload());
    await act(async () => pending.reject(new Error('obsolete error')));
    expect(node.textContent).toBe('current');
    expect(state.error).toBeNull();
  });

  it('action exposes pending, error, clear and successful retry', async () => {
    const pending = deferred();
    const action = vi.fn().mockReturnValueOnce(pending.promise).mockResolvedValueOnce({ saved: true });
    await render(<Action action={action} />);
    let result;
    await act(async () => { result = state.run().catch((error) => error); });
    expect(node.textContent).toBe('pending');
    await act(async () => { pending.reject(new Error('save failed')); await result; });
    expect(node.textContent).toBe('save failed');
    await act(async () => state.clearError());
    expect(state.error).toBeNull();
    await act(async () => state.run());
    expect(state.pending).toBe(false);
  });
});

describe('FE-04.1 pages using shared states', () => {
  it('course list shows loading then genuine empty data', async () => {
    const pending = deferred();
    services.getCoursesByClassification.mockReturnValueOnce(pending.promise);
    await render(<MyCoursesPage />);
    expect(node.querySelector('[role="status"]').textContent).toContain('Memuat');
    await act(async () => pending.resolve([]));
    expect(node.textContent).toContain('Tidak ada kursus pada filter ini.');
  });

  it('course list maps service failure and recovers through a filter request', async () => {
    services.getCoursesByClassification.mockRejectedValueOnce(new Error('Moodle unavailable')).mockResolvedValueOnce([course]);
    await render(<MyCoursesPage />);
    expect(node.querySelector('[role="alert"]').textContent).toContain('Moodle unavailable');
    await act(async () => {
      const select = node.querySelector('select');
      select.value = 'inprogress';
      select.dispatchEvent(new Event('change', { bubbles: true }));
    });
    expect(services.getCoursesByClassification).toHaveBeenLastCalledWith('inprogress');
    expect(node.querySelector('[role="alert"]')).toBeNull();
    expect(node.textContent).toContain('Pemrograman Web');
  });

  it('profile form shows disabled pending action, failure, and saved feedback', async () => {
    const pending = deferred();
    services.getProfile.mockResolvedValue({ teaching_style: 'Diskusi', language_preference: 'Bahasa Indonesia' });
    services.updateProfile.mockReturnValueOnce(pending.promise).mockResolvedValueOnce({ teaching_style: 'Diskusi' });
    await render(<TeachingProfilePage />);
    await act(async () => node.querySelector('form').requestSubmit());
    expect(node.querySelector('button[type="submit"]').disabled).toBe(true);
    await act(async () => pending.reject(new Error('Tidak dapat menyimpan profil')));
    expect(node.querySelector('[role="alert"]').textContent).toContain('Tidak dapat menyimpan profil');
    await act(async () => node.querySelector('form').requestSubmit());
    expect(node.textContent).toContain('Profil tersimpan.');
    expect(node.querySelector('[role="alert"]')).toBeNull();
  });
});
