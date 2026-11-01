import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../src/context/AuthProvider';
import { AppStateProvider } from '../src/context/AppStateProvider';
import App from '../src/App';
import { MOODLE_SESSION_KEY } from '../src/services/config';
import { login as backendLogin } from '../src/services/authService';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';
import { getWorkflow } from '../src/services/workflowService';

// Meniru backend nyata: API /courses belum ada, Generator AI berjalan di atas /workflows.
vi.mock('../src/services/config', async (original) => ({ ...(await original()), COURSE_API_AVAILABLE: false }));

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

  it('unggah RPS, hubungkan ke kursus lewat moodle-target, lalu pantau dan lepaskan', async () => {
    localStorage.setItem(MOODLE_SESSION_KEY, JSON.stringify({ token: 'mock-3-test' }));
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
    expect([...container.querySelectorAll('[aria-label="Bagian generator AI"] a')].map((a) => a.textContent)).toEqual(['Ringkasan', 'RPS']);
    await waitFor(() => container.querySelector('.event-log'), 'riwayat event');
    expect(await getWorkflow('workflow_001')).toMatchObject({ moodle_course_id: 2, rps_id: expect.any(String) });

    await act(async () => button('Lepas RPS dari kursus ini').click());
    await waitFor(() => container.querySelector('form.upload'), 'kembali ke unggah RPS');
    expect((await getWorkflow('workflow_001')).moodle_course_id).toBeNull();
  });
});
