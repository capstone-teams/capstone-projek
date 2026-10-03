import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../src/context/AuthProvider';
import App from '../src/App';
import { MOODLE_SESSION_KEY, USE_MOODLE_MOCK } from '../src/services/config';
import { login as backendLogin } from '../src/services/authService';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// Token mock Moodle: "mock-<userid>-..." (lihat mockMoodle.js). 3 = dosen, 5 = mahasiswa.
const TOKENS = { dosen: 'mock-3-test', mahasiswa: 'mock-5-test' };

let container;
let root;
let consoleError;

beforeAll(() => {
  configureMock({ latencyMs: 0, stepMs: 5 });
});

beforeEach(() => {
  resetMockDb();
  localStorage.clear();
  container = document.createElement('div');
  document.body.appendChild(container);
  consoleError = vi.spyOn(console, 'error');
});

afterEach(() => {
  act(() => root?.unmount());
  container.remove();
  consoleError.mockRestore();
});

async function render(path, as) {
  if (as) {
    localStorage.setItem(MOODLE_SESSION_KEY, JSON.stringify({ token: TOKENS[as] }));
    if (as === 'dosen') await backendLogin('dosen', 'x');
  }
  root = createRoot(container);
  await act(async () => {
    root.render(
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );
  });
}

async function waitForText(text, timeout = 3000) {
  const start = Date.now();
  while (!container.textContent.includes(text)) {
    if (Date.now() - start > timeout) throw new Error(`Teks "${text}" tidak muncul. Isi: ${container.textContent.slice(0, 400)}`);
    await act(() => new Promise((r) => setTimeout(r, 20)));
  }
}

describe('setup', () => {
  it('tes berjalan dengan mock Moodle', () => {
    expect(USE_MOODLE_MOCK).toBe(true);
  });
});

describe('login', () => {
  it('mengarahkan ke halaman login bila belum masuk', async () => {
    await render('/my/courses');
    await waitForText('Selamat datang kembali');
  });

  async function fillAndSubmit(username, password) {
    const setValue = (input, value) => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value);
      input.dispatchEvent(new Event('input', { bubbles: true }));
    };
    await act(async () => {
      setValue(container.querySelector('#username'), username);
      setValue(container.querySelector('#password'), password);
    });
    await act(async () => container.querySelector('form').requestSubmit());
  }

  it('login mahasiswa', async () => {
    await render('/login');
    await fillAndSubmit('mahasiswa', 'mahasiswa123');
    await waitForText('Halo, Andi!');
    expect(container.textContent).toContain('Mahasiswa');
  });

  it('login dosen', async () => {
    await render('/login');
    await fillAndSubmit('dosen', 'dosen123');
    await waitForText('Kursus yang Anda ajar');
  });

  it('menampilkan error untuk password salah', async () => {
    await render('/login');
    await fillAndSubmit('dosen', 'keliru');
    await waitForText('Username atau password salah');
  });

  it('tidak menampilkan kata dummy di halaman login', async () => {
    await render('/login');
    expect(container.textContent.toLowerCase()).not.toContain('dummy');
  });
});

describe('halaman dosen', () => {
  const pages = [
    ['/my', 'Kursus yang Anda ajar'],
    ['/my/courses', 'Basis Data'],
    ['/user/profile', 'Detail kursus'],
    ['/course/2', 'Minggu 1: Pengantar Pemrograman Web'],
    ['/course/2/participants', 'Andi Saputra'],
    ['/course/2/grades', 'Rekap nilai mahasiswa'],
    ['/course/2/mod/102', 'Konsep utama'],
    ['/course/2/mod/107', 'Ringkasan penilaian'],
    ['/course/2/mod/104', 'untuk membuka tautan'],
    ['/ai', 'Generation project'],
    ['/ai/rps', 'RPS-Pemrograman-Web-2026.pdf'],
    ['/ai/courses/course_project_001/plan', 'Rencana course · versi 1'],
    ['/ai/courses/course_project_002/plan', 'Setujui rencana'],
    ['/tidak-ada', 'Halaman tidak ditemukan'],
  ];

  it.each(pages)('render %s', async (path, text) => {
    await render(path, 'dosen');
    await waitForText(text);
    expect(consoleError).not.toHaveBeenCalled();
  });
});

describe('halaman mahasiswa', () => {
  const pages = [
    ['/my', 'Ringkasan belajar'],
    ['/course/3', 'Normalisasi'],
    ['/course/2/grades', 'Laporan nilai'],
    ['/course/2/mod/107', 'Status pengumpulan'],
    ['/ai', 'Khusus dosen'],
  ];

  it.each(pages)('render %s', async (path, text) => {
    await render(path, 'mahasiswa');
    await waitForText(text);
    expect(consoleError).not.toHaveBeenCalled();
  });

  it('tidak melihat menu Generator AI maupun kata dummy', async () => {
    await render('/my', 'mahasiswa');
    await waitForText('Halo, Andi!');
    expect(container.textContent).not.toContain('Generator AI');
    expect(container.textContent.toLowerCase()).not.toContain('dummy');
  });
});
