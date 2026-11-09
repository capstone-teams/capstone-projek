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
    ['format salah', new File(['x'], 'rps.txt', { type: 'text/plain' }), 'Format file harus PDF.'],
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

  it('menolak DOCX di klien tanpa mengirim ke backend', async () => {
    const uploadSpy = vi.spyOn(rpsService, 'uploadRps');
    await render();
    await waitFor(() => submitButton(), 'form');
    await pick(new File(['docx'], 'RPS-Final.docx'));
    expect(q('form.upload [role="alert"]').textContent).toContain('Format file harus PDF.');
    await act(async () => q('form.upload').requestSubmit());
    expect(uploadSpy).not.toHaveBeenCalled();
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
    expect(subscribe).toHaveBeenCalledWith('workflow_001', expect.any(Function), expect.any(Function));
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

  it('pesan gagal tetap dari backend setelah Proses ulang gagal lagi', async () => {
    await upload('rps-rusak.pdf');
    await waitFor(() => rowFor('rps-rusak.pdf').textContent.includes('Dokumen RPS gagal diproses'), 'pesan pertama');
    const retry = [...rowFor('rps-rusak.pdf').querySelectorAll('button')].find((b) => b.textContent === 'Proses ulang');
    await act(async () => retry.click());
    await waitFor(() => rowFor('rps-rusak.pdf').textContent.includes('Dokumen RPS gagal diproses') && rowFor('rps-rusak.pdf').textContent.includes('Gagal'), 'pesan setelah proses ulang');
    expect(rowFor('rps-rusak.pdf').textContent).not.toContain('Pemrosesan RPS gagal.');
  });

  it('pesan gagal diambil ulang bila GET /rps/{id} sempat gagal', async () => {
    await upload('rps-rusak.pdf');
    await waitFor(() => rowFor('rps-rusak.pdf').textContent.includes('Dokumen RPS gagal diproses'), 'pesan pertama');
    act(() => root.unmount());
    const real = rpsService.getRps;
    vi.spyOn(rpsService, 'getRps').mockRejectedValueOnce(new Error('jaringan')).mockImplementation(real);
    await render();
    await waitFor(() => rowFor('rps-rusak.pdf')?.textContent.includes('Dokumen RPS gagal diproses'), 'pesan setelah percobaan ulang', 8000);
  });

  const dialogButton = (text) => [...container.querySelectorAll('dialog button')].find((b) => b.textContent === text);
  const rowButton = (name, text) => [...rowFor(name).querySelectorAll('button')].find((b) => b.textContent === text);
  const pickAndUpload = async (name) => {
    await pick(new File(['%PDF'], name, { type: 'application/pdf' }));
    await act(async () => q('form.upload').requestSubmit());
  };

  it('RPS gagal dapat dihapus dengan konfirmasi dan tidak dapat dilihat lagi', async () => {
    await upload('rps-rusak.pdf');
    await waitFor(() => rowFor('rps-rusak.pdf').textContent.includes('Gagal'), 'RPS gagal');
    // Tombol hanya untuk RPS gagal; batal tidak mengubah apa pun.
    expect(rowButton('RPS-Pemrograman-Web-2026.pdf', 'Hapus')).toBeUndefined();
    await act(async () => rowButton('rps-rusak.pdf', 'Hapus').click());
    await act(async () => dialogButton('Batal').click());
    expect(rowFor('rps-rusak.pdf')).toBeTruthy();

    await act(async () => rowButton('rps-rusak.pdf', 'Hapus').click());
    await act(async () => dialogButton('Hapus').click());
    expect(rowFor('rps-rusak.pdf')).toBeUndefined();
    // Tidak ada tampilan atau pemulihan RPS yang dihapus.
    expect(container.textContent).not.toMatch(/yang dihapus|Pulihkan/);

    // Tetap hilang setelah halaman dimuat ulang.
    act(() => root.unmount());
    await render();
    await waitFor(() => rowFor('RPS-Pemrograman-Web-2026.pdf'), 'daftar dimuat');
    expect(rowFor('rps-rusak.pdf')).toBeUndefined();
  });

  it('mengunggah lagi file yang sudah dihapus menampilkannya kembali', async () => {
    await upload('rps-rusak.pdf');
    await waitFor(() => rowFor('rps-rusak.pdf').textContent.includes('Gagal'), 'RPS gagal');
    await act(async () => rowButton('rps-rusak.pdf', 'Hapus').click());
    await act(async () => dialogButton('Hapus').click());
    await pickAndUpload('rps-rusak.pdf');
    await waitFor(() => rowFor('rps-rusak.pdf'), 'tampil lagi');
  });

  it('hapus semua RPS yang gagal sekaligus', async () => {
    await upload('rps-rusak.pdf');
    await waitFor(() => rowFor('rps-rusak.pdf').textContent.includes('Gagal'), 'RPS gagal pertama');
    await pickAndUpload('rps-rusak-dua.pdf');
    await waitFor(() => rowFor('rps-rusak-dua.pdf')?.textContent.includes('Gagal'), 'RPS gagal kedua');
    await act(async () => [...container.querySelectorAll('button')].find((b) => b.textContent === 'Hapus semua yang gagal (2)').click());
    expect(container.querySelector('dialog').textContent).toContain('Hapus 2 RPS?');
    await act(async () => dialogButton('Hapus').click());
    expect(rowFor('rps-rusak.pdf')).toBeUndefined();
    expect(rowFor('rps-rusak-dua.pdf')).toBeUndefined();
    expect(rowFor('RPS-Pemrograman-Web-2026.pdf')).toBeTruthy();
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

  it('tab RPS menampilkan status dan tautan Pantau workflow ke tab Workflow', async () => {
    await render('/course/2/ai/rps');
    await waitFor(() => container.textContent.includes('Selesai dianalisis'), 'status di tab RPS');
    const monitor = [...container.querySelectorAll('a')].find((a) => a.textContent === 'Pantau workflow');
    expect(monitor.getAttribute('href')).toBe('/course/2/ai/workflows');
  });
});
