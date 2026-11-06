import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AiProjectStart from '../src/components/ai/course/AiProjectStart';
import { login as backendLogin } from '../src/services/authService';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';
import * as monitoringSocket from '../src/services/monitoringSocket';
import * as rpsService from '../src/services/rpsService';
import { RPS_STATUS, isRpsInProgress, rpsStatusMeta } from '../src/utils/rpsStatus';

// FE-08.2: halaman unggah dan daftar RPS (Generator AI kursus yang belum punya project), dengan backend mock
// lewat tests/setup/mockBackend.js: GET /rps/{id}, POST /rps/{id}/reanalyze, dan event WS /ws/workflows/{id}.
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe('FE-08.2 konstanta status RPS', () => {
  it('memuat enam status backend beserta label Bahasa Indonesia dan penanda visual', () => {
    expect(Object.values(RPS_STATUS)).toEqual(['UPLOADED', 'PROCESSING', 'PROCESSED', 'ANALYZING', 'ANALYZED', 'FAILED']);
    const labels = Object.values(RPS_STATUS).map((status) => rpsStatusMeta(status));
    labels.forEach((meta) => expect(meta).toMatchObject({ label: expect.any(String), tone: expect.any(String), marker: expect.any(String) }));
    expect(new Set(labels.map((meta) => meta.label)).size).toBe(6);
    expect(rpsStatusMeta(RPS_STATUS.FAILED)).toMatchObject({ tone: 'danger', marker: 'failed' });
    expect(rpsStatusMeta(RPS_STATUS.ANALYZED)).toMatchObject({ tone: 'success', marker: 'done' });
  });

  it('menandai status yang masih berjalan agar terus dipantau', () => {
    expect(isRpsInProgress({ status: 'PROCESSING' })).toBe(true);
    expect(isRpsInProgress({ status: 'ANALYZING' })).toBe(true);
    expect(isRpsInProgress({ status: 'PROCESSED', workflow_id: 'wf' })).toBe(true);
    expect(isRpsInProgress({ status: 'PROCESSED' })).toBe(false);
    expect(isRpsInProgress({ status: 'ANALYZED' })).toBe(false);
    expect(isRpsInProgress({ status: 'FAILED' })).toBe(false);
  });
});

describe('FE-08.2 status pemrosesan di halaman unggah dan daftar RPS', () => {
  let container;
  let root;
  beforeAll(() => configureMock({ latencyMs: 0, stepMs: 40 }));
  beforeEach(async () => {
    resetMockDb();
    localStorage.clear();
    await backendLogin('dosen', 'dosen123');
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={['/course/9/ai']}>
          <Routes>
            <Route path="/course/:courseId/ai" element={<AiProjectStart moodleCourse={{ id: 9, fullname: 'Kursus Uji' }} onCreated={() => {}} />} />
          </Routes>
        </MemoryRouter>,
      );
    });
  });
  afterEach(() => {
    act(() => root?.unmount());
    root = null;
    container.remove();
    vi.restoreAllMocks();
  });

  async function waitFor(check, label, timeout = 6000) {
    const start = Date.now();
    while (!check()) {
      if (Date.now() - start > timeout) throw new Error(`Tidak terpenuhi: ${label}. Isi: ${container.textContent.slice(0, 400)}`);
      await act(() => new Promise((resolve) => setTimeout(resolve, 20)));
    }
  }
  const row = (name) => [...container.querySelectorAll('ul[aria-label="Daftar RPS"] > li')].find((li) => li.textContent.includes(name));
  const badge = (name) => (row(name)?.querySelector('[title]')?.textContent ?? '').replace(/[✓✕]/g, '').trim();
  const link = (name, text) => [...(row(name)?.querySelectorAll('a') ?? [])].find((a) => a.textContent === text);
  const button = (name, text) => [...(row(name)?.querySelectorAll('button') ?? [])].find((b) => b.textContent === text);
  async function upload(name) {
    await waitFor(() => container.querySelector('form.upload'), 'form unggah');
    const input = container.querySelector('form.upload input[type="file"]');
    await act(async () => {
      Object.defineProperty(input, 'files', { value: [new File(['%PDF-1.4'], name, { type: 'application/pdf' })], configurable: true });
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await act(async () => container.querySelector('form.upload').requestSubmit());
    await waitFor(() => row(name), `${name} di daftar`);
  }

  it('status berubah otomatis sampai analyzed lewat event workflow, lalu tersedia tautan hasil analisis dan monitoring', async () => {
    const subscribe = vi.spyOn(monitoringSocket, 'subscribeWorkflowEvents');
    const detail = vi.spyOn(rpsService, 'getRps');
    await upload('RPS-Otomatis.pdf');
    const seen = new Set();
    await waitFor(() => {
      seen.add(badge('RPS-Otomatis.pdf'));
      return badge('RPS-Otomatis.pdf') === rpsStatusMeta(RPS_STATUS.ANALYZED).label;
    }, 'status Selesai dianalisis');

    // Tahap berjalan terlihat lebih dulu, lalu berubah sendiri tanpa memuat ulang halaman.
    const running = [RPS_STATUS.UPLOADED, RPS_STATUS.PROCESSING, RPS_STATUS.PROCESSED, RPS_STATUS.ANALYZING].map((status) => rpsStatusMeta(status).label);
    expect([...seen].some((label) => running.includes(label))).toBe(true);
    // Status dari GET /rps/{id}, dipicu event workflow (FE-10.2).
    expect(subscribe).toHaveBeenCalledWith(expect.stringMatching(/^workflow_/), expect.any(Function), expect.any(Function));
    expect(detail).toHaveBeenCalled();

    const id = detail.mock.calls.at(-1)[0];
    expect(link('RPS-Otomatis.pdf', 'Lihat hasil analisis').getAttribute('href')).toBe(`/course/9/ai/rps?rps=${id}`);
    expect(link('RPS-Otomatis.pdf', 'Pantau workflow').getAttribute('href')).toMatch(/^\/course\/9\/ai\/workflows\?workflow=workflow_\d+$/);
  });

  it('RPS yang gagal dianalisis menampilkan pesan dari backend dan dapat dianalisis ulang dari UI', async () => {
    const reanalyze = vi.spyOn(rpsService, 'reanalyzeRps');
    await upload('RPS-gagal-analisis.pdf');
    await waitFor(() => badge('RPS-gagal-analisis.pdf') === rpsStatusMeta(RPS_STATUS.FAILED).label, 'status Gagal');
    await waitFor(() => row('RPS-gagal-analisis.pdf').querySelector('.text-danger[role="status"]'), 'pesan gagal');
    expect(row('RPS-gagal-analisis.pdf').querySelector('.text-danger[role="status"]').textContent).not.toBe('');
    expect(link('RPS-gagal-analisis.pdf', 'Lihat hasil analisis')).toBeUndefined();

    await act(async () => button('RPS-gagal-analisis.pdf', 'Analisis ulang').click());
    expect(reanalyze).toHaveBeenCalledTimes(1);
    await waitFor(() => badge('RPS-gagal-analisis.pdf') === rpsStatusMeta(RPS_STATUS.ANALYZED).label, 'Selesai setelah analisis ulang');
    expect(link('RPS-gagal-analisis.pdf', 'Lihat hasil analisis')).toBeTruthy();
  });

  it('polling tetap memperbarui status bila WebSocket tidak tersedia', async () => {
    vi.spyOn(monitoringSocket, 'subscribeWorkflowEvents').mockImplementation((_id, _onEvent, onStatus) => {
      onStatus?.(monitoringSocket.SOCKET_STATUS.OFFLINE);
      return () => {};
    });
    await upload('RPS-Polling.pdf');
    await waitFor(() => badge('RPS-Polling.pdf') === rpsStatusMeta(RPS_STATUS.ANALYZED).label, 'Selesai lewat polling', 15000);
  }, 20000);
});
