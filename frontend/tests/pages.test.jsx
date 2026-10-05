import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../src/context/AuthProvider';
import { AppStateProvider } from '../src/context/AppStateProvider';
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
          <AppStateProvider>
            <App />
          </AppStateProvider>
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
    await waitForText('Masuk ke akun Anda');
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
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it('tidak menolak username yang benar dan menampilkan notifikasi untuk password yang salah', async () => {
    await render('/login');
    await fillAndSubmit('dosen', 'keliru');
    await waitForText('Username atau password salah');
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('Login gagal');
  });

  it('menyediakan kontrol emoji mata, tombol Google, dan menyembunyikan tautan Masuk di navbar', async () => {
    await render('/login');

    const password = container.querySelector('#password');
    const passwordToggle = container.querySelector('[aria-label="Tampilkan kata sandi"]');
    expect(password.type).toBe('password');
    expect(passwordToggle).not.toBeNull();
    expect(container.querySelector('header a')?.textContent).not.toContain('Masuk');

    await act(async () => passwordToggle.click());
    expect(password.type).toBe('text');
    expect(container.querySelector('[aria-label="Sembunyikan kata sandi"]')).not.toBeNull();

    const googleButton = [...container.querySelectorAll('button')].find((button) => button.textContent.includes('Lanjutkan dengan Google'));
    await act(async () => googleButton.click());
    await waitForText('Login menggunakan Google belum tersedia');
  });

  it('membuka halaman pemulihan kata sandi dari login', async () => {
    await render('/login');
    await act(async () => container.querySelector('a[href="/forgot-password"]').click());

    await waitForText('Lupa kata sandi?');
    expect(container.querySelector('#recovery-username')).not.toBeNull();
    expect(container.querySelector('form').getAttribute('action')).toContain('/login/forgot_password.php');
  });

  it('menampilkan pemberitahuan saat mengirim pemulihan dalam mode demo', async () => {
    await render('/forgot-password');
    const recoveryInput = container.querySelector('#recovery-username');
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(recoveryInput, 'dosen');
    await act(async () => recoveryInput.dispatchEvent(new Event('input', { bubbles: true })));
    await act(async () => container.querySelector('form').requestSubmit());
    await waitForText('Pemulihan kata sandi belum tersedia');
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
