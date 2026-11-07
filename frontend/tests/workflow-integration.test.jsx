import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../src/context/AuthProvider';
import { AppStateProvider } from '../src/context/AppStateProvider';
import App from '../src/App';
import { login as backendLogin } from '../src/services/authService';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';
import { getWorkflow } from '../src/services/workflowService';

// Meniru backend nyata: API /courses belum ada, Generator AI berjalan di atas /workflows.
vi.mock('../src/services/config', async (original) => ({ ...(await original()), COURSE_API_AVAILABLE: false, RPS_DELETE_AVAILABLE: false }));

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe('Generator AI tanpa API /courses', () => {
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
  });
  async function waitFor(check, label, timeout = 5000) {
    const start = Date.now();
    while (!check()) {
      if (Date.now() - start > timeout) throw new Error(`Tidak terpenuhi: ${label}. Isi: ${container.textContent.slice(-300)}`);
      await act(() => new Promise((r) => setTimeout(r, 20)));
    }
  }
  const button = (text) => [...container.querySelectorAll('button')].find((b) => b.textContent === text);

  it('RPS analyzed tanpa workflow tetap dapat dibuka hasil analisisnya dan tidak dapat dihubungkan', async () => {
    await backendLogin('dosen', 'dosen123');
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={['/course/2/ai']}>
          <AuthProvider><AppStateProvider><App /></AppStateProvider></AuthProvider>
        </MemoryRouter>,
      );
    });
    const link = () => [...container.querySelectorAll('a')].find((a) => a.textContent === 'Lihat hasil analisis');
    await waitFor(link, 'tautan hasil analisis');
    expect(button('Hubungkan RPS').disabled).toBe(true);
    await act(async () => link().click());
    await waitFor(() => container.querySelector('section[aria-label^="CPMK:"]'), 'hasil analisis');
    expect([...container.querySelectorAll('a')].some((a) => a.textContent === 'Kembali ke daftar RPS')).toBe(true);
  });

  it('tombol Hapus RPS gagal disembunyikan selama backend belum punya DELETE, dan RPS yang pernah dihapus tampil lagi', async () => {
    await backendLogin('dosen', 'dosen123');
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={['/course/2/ai']}>
          <AuthProvider><AppStateProvider><App /></AppStateProvider></AuthProvider>
        </MemoryRouter>,
      );
    });
    await waitFor(() => container.querySelector('form.upload'), 'form unggah');
    const input = container.querySelector('form.upload input[type="file"]');
    const upload = async (name) => {
      await act(async () => {
        Object.defineProperty(input, 'files', { value: [new File(['%PDF'], name, { type: 'application/pdf' })], configurable: true });
        input.dispatchEvent(new Event('change', { bubbles: true }));
      });
      await act(async () => container.querySelector('form.upload').requestSubmit());
    };
    await upload('rps-rusak.pdf');
    await upload('rps-rusak-dua.pdf');
    const rows = () => [...container.querySelectorAll('ul[aria-label="Daftar RPS"] > li')];
    await waitFor(() => rows().filter((row) => row.textContent.includes('Gagal')).length === 2, 'dua RPS gagal');
    expect(button('Hapus')).toBeUndefined();
    expect(container.textContent).not.toMatch(/Hapus semua yang gagal/);
    expect(button('Proses ulang')).toBeTruthy();
  });

  it('unggah RPS, hubungkan ke kursus lewat moodle-target, lalu pantau dan lepaskan', async () => {
    await backendLogin('dosen', 'dosen123');
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={['/course/2/ai']}>
          <AuthProvider><AppStateProvider><App /></AppStateProvider></AuthProvider>
        </MemoryRouter>,
      );
    });
    await waitFor(() => container.querySelector('form.upload'), 'form unggah');
    expect(button('Hubungkan RPS').disabled).toBe(true);
    expect(container.textContent).not.toContain('Mulai generator AI');

    const input = container.querySelector('form.upload input[type="file"]');
    await act(async () => {
      Object.defineProperty(input, 'files', { value: [new File(['%PDF'], 'RPS-Nyata.pdf', { type: 'application/pdf' })], configurable: true });
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await act(async () => container.querySelector('form.upload').requestSubmit());
    await waitFor(() => !button('Hubungkan RPS')?.disabled && container.textContent.includes('RPS-Nyata.pdf'), 'RPS selesai dianalisis');

    await act(async () => button('Hubungkan RPS').click());
    await waitFor(() => container.textContent.includes('Status workflow'), 'ringkasan workflow');
    expect([...container.querySelectorAll('[aria-label="Bagian generator AI"] a')].map((a) => a.textContent)).toEqual(['Ringkasan', 'RPS', 'Course Target', 'Workflow']);
    await waitFor(() => container.querySelector('.event-log'), 'riwayat event');
    expect(await getWorkflow('workflow_001')).toMatchObject({ moodle_course_id: 2, rps_id: expect.any(String) });

    await act(async () => button('Lepas RPS dari kursus ini').click());
    await waitFor(() => container.querySelector('form.upload'), 'kembali ke unggah RPS');
    expect((await getWorkflow('workflow_001')).moodle_course_id).toBeNull();
  }, 15000);
});
