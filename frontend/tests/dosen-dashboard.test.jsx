import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../src/context/AuthProvider';
import { AppStateProvider } from '../src/context/AppStateProvider';
import App from '../src/App';
import { login as backendLogin } from '../src/services/authService';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe('Dashboard Dosen (Clean Restored Layout)', () => {
  let container;
  let root;

  beforeAll(() => {
    configureMock({ latencyMs: 0, stepMs: 5 });
  });

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

  async function renderDashboard() {
    await backendLogin('dosen', 'dosen123');
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={['/my']}>
          <AuthProvider>
            <AppStateProvider>
              <App />
            </AppStateProvider>
          </AuthProvider>
        </MemoryRouter>,
      );
    });
  }

  async function waitFor(check, label, timeout = 4000) {
    const start = Date.now();
    while (!check()) {
      if (Date.now() - start > timeout) {
        throw new Error(`Timeout: ${label}. Isi: ${container.textContent.slice(0, 400)}`);
      }
      await act(() => new Promise((r) => setTimeout(r, 20)));
    }
  }

  it('menampilkan salam, timeline, kursus berjalan, dan kursus yang diajar dosen', async () => {
    await renderDashboard();
    await waitFor(() => container.textContent.includes('Halo,'), 'Salam dosen');

    expect(container.textContent).toContain('Timeline');
    expect(container.textContent).toContain('Kursus yang Anda ajar');
    expect(container.textContent).toMatch(/Kursus berjalan|Kursus yang baru diakses/);
  });

  it('tidak menampilkan card RPS & Dokumen Akademik atau tombol unggah di dasbor', async () => {
    await renderDashboard();
    await waitFor(() => container.textContent.includes('Halo,'), 'Salam dosen');

    expect(container.textContent).not.toContain('RPS & Dokumen Akademik');
    expect(container.textContent).not.toContain('Belum ada dokumen RPS.');

    const buttons = [...container.querySelectorAll('button')];
    const uploadBtn = buttons.find((b) => b.textContent.includes('Unggah'));
    expect(uploadBtn).toBeFalsy();
  });

  it('menampilkan daftar kursus yang diajar dosen dengan tautan navigasi ke kursus', async () => {
    await renderDashboard();
    await waitFor(() => container.textContent.includes('Kursus yang Anda ajar'), 'Kursus yang diajar');

    const links = [...container.querySelectorAll('a')];
    const courseLinks = links.filter((a) => a.getAttribute('href')?.startsWith('/course/'));
    expect(courseLinks.length).toBeGreaterThan(0);
  });
});
