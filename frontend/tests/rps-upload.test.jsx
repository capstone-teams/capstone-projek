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
import * as monitoringSocket from '../src/services/monitoringSocket';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
vi.setConfig({ testTimeout: 20000 });

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
    expect(rowFor('RPS-Pemrograman-Web-2026.pdf').textContent).toContain('Selesai dianalisis');
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
    // Pemrosesan dipantau sampai selesai dianalisis.
    await waitFor(() => rowFor('RPS-Basis-Data.pdf').textContent.includes('Selesai dianalisis'), 'status Selesai dianalisis');
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

  it('konversi yang gagal menampilkan pesannya dan dapat diproses ulang', async () => {
    await render();
    await waitFor(() => submitButton(), 'form');
    await pick(new File(['%PDF'], 'rps-rusak.pdf', { type: 'application/pdf' }));
    await act(async () => q('form.upload').requestSubmit());
    await waitFor(() => rowFor('rps-rusak.pdf')?.textContent.includes('Gagal'), 'status Gagal');
    expect(rowFor('rps-rusak.pdf').textContent).toContain('Dokumen RPS gagal diproses');
    const labels = [...rowFor('rps-rusak.pdf').querySelectorAll('button')].map((b) => b.textContent);
    expect(labels).toContain('Proses ulang');
    expect(labels).not.toContain('Analisis ulang');
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
    // Tanpa GET /rps tidak ada workflow_id; status terakhir dari GET /rps/{id} bisa PROCESSED atau ANALYZED.
    await waitFor(() => /Siap dianalisis|Selesai dianalisis/.test(rowFor('RPS-Sesi.pdf').textContent), 'dipantau lewat GET /rps/{id}');
  });

  it('RPS yang selesai diproses dapat dipilih untuk kursus', async () => {
    await render();
    await waitFor(() => submitButton(), 'form');
    await pick(new File(['%PDF'], 'RPS-Basis-Data.pdf', { type: 'application/pdf' }));
    await act(async () => q('form.upload').requestSubmit());
    await waitFor(() => rowFor('RPS-Basis-Data.pdf')?.textContent.includes('Selesai dianalisis'), 'status Selesai dianalisis');
    const options = [...q('select').options].map((option) => option.textContent);
    expect(options).toEqual(['RPS-Basis-Data.pdf', 'RPS-Pemrograman-Web-2026.pdf']);
  });

  it('mahasiswa yang membuka Generator AI melihat halaman akses ditolak', async () => {
    await render(AI_START, 'mahasiswa');
    await waitFor(() => container.textContent.includes('Akses ditolak'), '403');
    expect(q('form.upload')).toBeNull();
  });
});

describe('FE-08.2 status pemrosesan RPS', () => {
  async function upload(name) {
    await render();
    await waitFor(() => submitButton(), 'form');
    await pick(new File(['%PDF'], name, { type: 'application/pdf' }));
    await act(async () => q('form.upload').requestSubmit());
    await waitFor(() => rowFor(name), name + ' di daftar');
  }
  it('status berubah otomatis melewati tahap analisis hingga selesai, tanpa memuat ulang', async () => {
    // Langkah mock 2 detik (lebih realistis): polling menemukan PROCESSED + workflow_id, lalu event
    // workflow memperbarui status ke ANALYZING dan ANALYZED tanpa menunggu polling berikutnya.
    configureMock({ latencyMs: 0, stepMs: 2000 });
    const subscribe = vi.spyOn(monitoringSocket, 'subscribeWorkflowEvents');
    const reload = vi.spyOn(rpsService, 'listRps');
    await upload('RPS-Otomatis.pdf');
    const seenLabels = new Set();
    await waitFor(() => {
      // Teks badge tanpa penanda visual (✓/✕).
      const badge = (rowFor('RPS-Otomatis.pdf').querySelector('[title]')?.textContent ?? '').replace(/[✓✕]/g, '').trim();
      seenLabels.add(badge);
      return badge === 'Selesai dianalisis';
    }, 'Selesai dianalisis', 13000);
    configureMock({ latencyMs: 0, stepMs: 5 });
    expect(subscribe).toHaveBeenCalledWith('workflow_001', expect.any(Function));
    expect([...seenLabels]).toEqual(expect.arrayContaining(['Diproses', 'Dianalisis', 'Selesai dianalisis']));
    const row = rowFor('RPS-Otomatis.pdf');
    expect(row.textContent).toMatch(/workflow_\d+/);
    expect(row.querySelector('[role="status"]')).toBeNull();
    // Status diperoleh dari GET /rps/{id} dan event workflow, bukan dari memuat ulang halaman.
    expect(reload.mock.calls.length).toBeLessThan(10);
  });

  it('RPS yang gagal dianalisis dapat dianalisis ulang dari UI', async () => {
    const reanalyze = vi.spyOn(rpsService, 'reanalyzeRps');
    await upload('rps-gagal-analisis.pdf');
    await waitFor(() => rowFor('rps-gagal-analisis.pdf').textContent.includes('Gagal'), 'status Gagal');
    expect(rowFor('rps-gagal-analisis.pdf').textContent).toContain('Analisis RPS gagal. Coba analisis ulang.');
    const button = [...rowFor('rps-gagal-analisis.pdf').querySelectorAll('button')].find((b) => b.textContent === 'Analisis ulang');
    await act(async () => button.click());
    expect(reanalyze).toHaveBeenCalledOnce();
    await waitFor(() => rowFor('rps-gagal-analisis.pdf').textContent.includes('Selesai dianalisis'), 'analisis ulang selesai');
    expect(rowFor('rps-gagal-analisis.pdf').textContent).not.toContain('Analisis RPS gagal');
  });

  it('backend tanpa orkestrator: RPS PROCESSED tanpa workflow dapat dianalisis dari UI', async () => {
    const reanalyze = vi.spyOn(rpsService, 'reanalyzeRps');
    await upload('rps-tanpa-analisis.pdf');
    await waitFor(() => rowFor('rps-tanpa-analisis.pdf').textContent.includes('Siap dianalisis'), 'status Siap dianalisis');
    const row = () => rowFor('rps-tanpa-analisis.pdf');
    expect(row().textContent).toContain('Belum dibuat');
    const button = [...row().querySelectorAll('button')].find((b) => b.textContent === 'Analisis RPS');
    expect(button).toBeTruthy();
    await act(async () => button.click());
    expect(reanalyze).toHaveBeenCalledOnce();
    await waitFor(() => row().textContent.includes('Selesai dianalisis'), 'analisis selesai');
    expect(row().textContent).toMatch(/workflow_\d+/);
    expect([...row().querySelectorAll('button')].map((b) => b.textContent)).not.toContain('Analisis RPS');
  });

  it('pesan gagal dibaca dari GET /rps/{id} untuk RPS gagal yang dimuat dari daftar', async () => {
    await upload('rps-rusak.pdf');
    await waitFor(() => rowFor('rps-rusak.pdf').textContent.includes('Gagal'), 'status Gagal');
    // Muat ulang halaman: daftar GET /rps tidak memuat processing_error_message.
    act(() => root.unmount());
    const getRps = vi.spyOn(rpsService, 'getRps');
    await render();
    await waitFor(() => rowFor('rps-rusak.pdf')?.textContent.includes('Dokumen RPS gagal diproses'), 'pesan dari GET /rps/{id}');
    expect(getRps).toHaveBeenCalledTimes(1);
  });

  it('menampilkan ringkasan hasil analisis untuk RPS yang selesai dianalisis', async () => {
    await render();
    await waitFor(() => rowFor('RPS-Pemrograman-Web-2026.pdf'), 'RPS contoh');
    const toggle = [...rowFor('RPS-Pemrograman-Web-2026.pdf').querySelectorAll('button')].find((b) => b.textContent === 'Lihat hasil analisis');
    await act(async () => toggle.click());
    await waitFor(() => q('[aria-label="Ringkasan hasil analisis"]'), 'ringkasan');
    const summary = q('[aria-label="Ringkasan hasil analisis"]').textContent;
    expect(summary).toContain('16 minggu');
    expect(summary).toMatch(/\d+ capaian/);
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
  });

  it('tab RPS menampilkan status dan tautan Pantau workflow ke Ringkasan', async () => {
    await render('/course/2/ai/rps');
    await waitFor(() => container.textContent.includes('Selesai dianalisis'), 'status di tab RPS');
    const monitor = [...container.querySelectorAll('a')].find((a) => a.textContent === 'Pantau workflow');
    expect(monitor.getAttribute('href')).toBe('/course/2/ai');
  });
});
