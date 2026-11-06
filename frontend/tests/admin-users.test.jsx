import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AdminUsersPage from '../src/pages/admin/AdminUsersPage';
import { api } from '../src/services/apiClient';
import { getUser, listUsers } from '../src/services/adminService';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const USERS = [
  { id: 'u1', username: 'dosen.demo', firstname: 'Dosen', lastname: 'Demo', email: 'dosen.demo@itk.ac.id', role: 'INSTRUCTOR', status: 'ACTIVE', created_at: '2026-11-01T08:00:00Z' },
  { id: 'u2', username: '11231023', firstname: 'Mahasiswa', lastname: 'Demo', email: '11231023@student.itk.ac.id', role: 'STUDENT', status: 'INACTIVE', created_at: '2026-11-01T08:00:00Z' },
];

describe('adminService', () => {
  afterEach(() => vi.restoreAllMocks());
  it('memakai GET /admin/users dan GET /admin/users/{id}', async () => {
    const get = vi.spyOn(api, 'get').mockImplementation(async (path) => (path === '/admin/users' ? { users: USERS } : USERS[0]));
    expect(await listUsers()).toEqual(USERS);
    expect(await getUser('u1')).toEqual(USERS[0]);
    expect(get.mock.calls.map(([path]) => path)).toEqual(['/admin/users', '/admin/users/u1']);
  });
});

describe('Halaman Pengguna (admin)', () => {
  let node;
  let root;
  let get;
  beforeEach(() => {
    get = vi.spyOn(api, 'get').mockImplementation(async (path) => (path === '/admin/users' ? { users: USERS } : USERS.find((u) => path.endsWith(u.id))));
    node = document.createElement('div');
    document.body.appendChild(node);
  });
  afterEach(async () => {
    await act(async () => root?.unmount());
    root = null;
    node.remove();
    vi.restoreAllMocks();
  });
  async function render() {
    root ??= createRoot(node);
    await act(async () => root.render(<MemoryRouter><AdminUsersPage /></MemoryRouter>));
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
  }
  const items = () => [...node.querySelectorAll('ul[aria-label="Daftar pengguna"] > li')];
  const setValue = async (element, value) => {
    const proto = element.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    await act(async () => {
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(element, value);
      element.dispatchEvent(new Event(element.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }));
    });
  };

  it('menampilkan semua pengguna dengan nama, username, email, dan peran', async () => {
    await render();
    expect(items()).toHaveLength(2);
    expect(items()[0].textContent).toContain('Dosen Demo');
    expect(items()[0].textContent).toContain('dosen.demo@itk.ac.id');
    expect(items()[0].textContent).toContain('Dosen');
    expect(items()[1].textContent).toContain('Mahasiswa');
  });

  it('memilih pengguna memuat detailnya dari GET /admin/users/{id}', async () => {
    await render();
    await act(async () => items()[1].querySelector('button').click());
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
    expect(get).toHaveBeenCalledWith('/admin/users/u2');
    const detail = node.querySelector('[aria-label="Detail pengguna"]');
    expect(detail.textContent).toContain('11231023@student.itk.ac.id');
    expect(detail.textContent).toContain('Nonaktif');
  });

  it('mencari dan menyaring berdasarkan peran', async () => {
    await render();
    await setValue(node.querySelector('input[aria-label="Cari pengguna"]'), '1123');
    expect(items()).toHaveLength(1);
    await setValue(node.querySelector('input[aria-label="Cari pengguna"]'), '');
    await setValue(node.querySelector('select[aria-label="Filter peran"]'), 'INSTRUCTOR');
    expect(items().map((li) => li.textContent)).toEqual([expect.stringContaining('Dosen Demo')]);
  });

  it('galat memuat menampilkan pesan dan Coba lagi', async () => {
    get.mockRejectedValueOnce(Object.assign(new Error('Akses ditolak.'), { status: 403 }));
    await render();
    expect(node.querySelector('[role="alert"]').textContent).toContain('Akses ditolak.');
    await act(async () => [...node.querySelectorAll('button')].find((b) => b.textContent === 'Coba lagi').click());
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
    expect(items()).toHaveLength(2);
  });
});
