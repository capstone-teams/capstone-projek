import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../src/context/AuthProvider';
import { AppStateProvider } from '../src/context/AppStateProvider';
import App from '../src/App';
import { MOODLE_SESSION_KEY } from '../src/services/config';
import { login as backendLogin } from '../src/services/authService';
import * as rpsService from '../src/services/rpsService';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const TOKENS = { dosen: 'mock-3-test', mahasiswa: 'mock-5-test' };
let container;
let root;

beforeAll(() => configureMock({ latencyMs: 0, stepMs: 5 }));
beforeEach(() => {
  resetMockDb();
  localStorage.clear();
  container = document.createElement('div');
  document.body.appendChild(container);
});
afterEach(() => {
  act(() => root?.unmount());
  root = null;
  container.remove();
  vi.restoreAllMocks();
});

// Basis Data (kursus 3) belum punya project generator: tab Generator AI menampilkan kartu "1. RPS mata kuliah".
const AI_START = '/course/3/ai';

async function render(path = AI_START, who = 'dosen') {
  localStorage.setItem(MOODLE_SESSION_KEY, JSON.stringify({ token: TOKENS[who] }));
  await backendLogin(who, `${who}123`);
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

async function waitFor(check, label, timeout = 5000) {
  const start = Date.now();
  while (!check()) {
    if (Date.now() - start > timeout) throw new Error(`Tidak terpenuhi: ${label}. Isi: ${container.textContent.slice(0, 400)}`);
    await act(() => new Promise((r) => setTimeout(r, 20)));
  }
}
const q = (selector) => container.querySelector(selector);
const submitButton = () => q('form.upload button[type="submit"]');
const rows = () => [...container.querySelectorAll('ul[aria-label="Daftar RPS"] > li')];
const rowFor = (name) => rows().find((row) => row.textContent.includes(name));

function pick(file) {
  const input = q('form.upload input[type="file"]');
  Object.defineProperty(input, 'files', { value: [file], configurable: true });
  return act(async () => input.dispatchEvent(new Event('change', { bubbles: true })));
}
function sized(name, bytes) {
  const file = new File(['%PDF'], name, { type: 'application/pdf' });
  Object.defineProperty(file, 'size', { value: bytes });
  return file;
}

describe('FE-08.1 unggah RPS di Generator AI', () => {
  it('kartu RPS di Generator AI menampilkan formulir unggah dan daftar RPS milik dosen', async () => {
    await render();
    await waitFor(() => rowFor('RPS-Pemrograman-Web-2026.pdf'), 'RPS contoh di daftar');
    expect(container.textContent).toContain('1. RPS mata kuliah');
    expect(q('form.upload')).not.toBeNull();
    // Tidak ada halaman RPS terpisah di menu.
    expect([...container.querySelectorAll('nav[aria-label="Navigasi situs"] a')].map((a) => a.textContent)).toEqual(['Dasbor', 'Kursusku']);
    expect(rowFor('RPS-Pemrograman-Web-2026.pdf').textContent).toContain('Siap');
    expect(rowFor('RPS-Pemrograman-Web-2026.pdf').textContent).toContain('Belum dibuat');
  });

  it.each([
    ['format salah', new File(['x'], 'rps.txt', { type: 'text/plain' }), 'Format file harus PDF atau DOCX.'],
    ['ukuran berlebih', sized('rps-besar.pdf', 25 * 1024 * 1024), 'Ukuran file 25.0 MB melebihi batas 20.0 MB.'],
    ['file kosong', sized('kosong.pdf', 0), 'File kosong. Pilih file RPS yang berisi dokumen.'],
  ])('menolak %s sebelum dikirim', async (_, file, message) => {
    const upload = vi.spyOn(rpsService, 'uploadRps');
    await render();
    await waitFor(() => submitButton(), 'form');
    await pick(file);
    expect(q('form.upload [role="alert"]').textContent).toBe(message);
    expect(q('form.upload input[type="file"]').getAttribute('aria-invalid')).toBe('true');
    expect(submitButton().disabled).toBe(true);
    await act(async () => q('form.upload').requestSubmit());
    expect(upload).not.toHaveBeenCalled();
  });

  it('mengunggah PDF, menampilkannya di daftar, dan memulai pemrosesan', async () => {
    const process = vi.spyOn(rpsService, 'processRps');
    await render();
    await waitFor(() => rows().length > 0, 'daftar awal');
    await pick(new File(['%PDF-1.7'], 'RPS-Basis-Data.pdf', { type: 'application/pdf' }));
    expect(q('form.upload [role="alert"]')).toBeNull();
    expect(submitButton().disabled).toBe(false);

    await act(async () => q('form.upload').requestSubmit());
    await waitFor(() => rowFor('RPS-Basis-Data.pdf'), 'RPS baru di daftar');
    expect(process).toHaveBeenCalledOnce();
    expect(rowFor('RPS-Basis-Data.pdf').textContent).toContain('Baru');
    expect(rows()[0]).toBe(rowFor('RPS-Basis-Data.pdf'));
    // Pemrosesan dipantau sampai selesai.
    await waitFor(() => rowFor('RPS-Basis-Data.pdf').textContent.includes('Siap'), 'status Siap');
    expect(q('form.upload input[type="file"]').value).toBe('');
  });

  it('menampilkan catatan DOCX dan pesan backend bila DOCX belum diterima server', async () => {
    await render();
    await waitFor(() => submitButton(), 'form');
    await pick(new File(['docx'], 'RPS-Final.docx'));
    expect(container.textContent).toContain('pemrosesannya di backend menyusul pada M03');
    await act(async () => q('form.upload').requestSubmit());
    await waitFor(() => q('form.upload [role="alert"]')?.textContent.includes('File RPS tidak valid.'), 'pesan backend');
    expect(rowFor('RPS-Final.docx')).toBeUndefined();
  });

  it('menampilkan status gagal dengan pesannya dan dapat memproses ulang', async () => {
    await render();
    await waitFor(() => submitButton(), 'form');
    await pick(new File(['%PDF'], 'rps-rusak.pdf', { type: 'application/pdf' }));
    await act(async () => q('form.upload').requestSubmit());
    await waitFor(() => rowFor('rps-rusak.pdf')?.textContent.includes('Gagal'), 'status Gagal');
    const retry = [...rowFor('rps-rusak.pdf').querySelectorAll('button')].find((b) => b.textContent === 'Proses ulang');
    expect(retry).toBeTruthy();
  });

  it('tetap menampilkan RPS sesi ini bila GET /rps belum tersedia (501)', async () => {
    const { ApiError } = await import('../src/services/apiClient');
    vi.spyOn(rpsService, 'listRps').mockRejectedValue(new ApiError(501, 'NOT_IMPLEMENTED', 'Belum diimplementasikan.'));
    await render();
    await waitFor(() => container.textContent.includes('Daftar RPS dari server belum tersedia'), 'info 501');
    expect(container.textContent).toContain('Belum ada RPS.');
    await pick(new File(['%PDF'], 'RPS-Sesi.pdf', { type: 'application/pdf' }));
    await act(async () => q('form.upload').requestSubmit());
    await waitFor(() => rowFor('RPS-Sesi.pdf'), 'RPS sesi di daftar');
    await waitFor(() => rowFor('RPS-Sesi.pdf').textContent.includes('Siap'), 'dipantau lewat GET /rps/{id}');
  });

  it('RPS yang selesai diproses dapat dipilih untuk kursus', async () => {
    await render();
    await waitFor(() => submitButton(), 'form');
    await pick(new File(['%PDF'], 'RPS-Basis-Data.pdf', { type: 'application/pdf' }));
    await act(async () => q('form.upload').requestSubmit());
    await waitFor(() => rowFor('RPS-Basis-Data.pdf')?.textContent.includes('Siap'), 'status Siap');
    const options = [...q('select').options].map((option) => option.textContent);
    expect(options).toEqual(['RPS-Basis-Data.pdf', 'RPS-Pemrograman-Web-2026.pdf']);
  });

  it('mahasiswa yang membuka Generator AI melihat halaman akses ditolak', async () => {
    await render(AI_START, 'mahasiswa');
    await waitFor(() => container.textContent.includes('Akses ditolak'), '403');
    expect(q('form.upload')).toBeNull();
  });
});
