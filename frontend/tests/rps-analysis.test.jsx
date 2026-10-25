import { afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../src/context/AuthProvider';
import { AppStateProvider } from '../src/context/AppStateProvider';
import App from '../src/App';
import RpsAnalysisDetails from '../src/components/ai/course/RpsAnalysisDetails';
import { MOODLE_SESSION_KEY } from '../src/services/config';
import { login as backendLogin } from '../src/services/authService';
import { buildRpsStructuredData } from '../src/services/mock/mockData';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';
import { SECTION_STATUS, danglingReferences, normalizeRpsAnalysis, sectionStatuses } from '../src/utils/rpsAnalysis';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const sample = () => normalizeRpsAnalysis({ rps_id: 'rps_001', analyzed_at: '2026-10-21T08:01:10Z', data: buildRpsStructuredData() });
const incomplete = () => normalizeRpsAnalysis({ rps_id: 'rps_002', data: buildRpsStructuredData({ incomplete: true }) });

describe('FE-08.3 utilitas hasil analisis', () => {
  it('menormalkan response §6.4 dan mengurutkan minggu', () => {
    const analysis = normalizeRpsAnalysis({ rps_id: 'x', data: { weeks: [{ week: 2 }, { week: 1, topics: ['A'] }] } });
    expect(analysis.weeks.map((week) => week.week)).toEqual([1, 2]);
    expect(analysis.weeks[1]).toMatchObject({ week_type: 'regular', topics: [], sub_cpmk: [], assessment: null });
    expect(analysis).toMatchObject({ cpl: [], cpmk: [], subCpmk: [], assessments: [], references: [], extraction: null });
  });

  it('menemukan rujukan silang tanpa sasaran seperti validate_references backend', () => {
    expect(danglingReferences(sample())).toEqual([{ source: 'sub_cpmk', field: 'cpmk_ids', value: 'CPMK-4', week: null }]);
    // Daftar sasaran kosong dilewati: tidak menghasilkan derau.
    expect(danglingReferences(incomplete()).filter((item) => item.field === 'cpl_ids')).toEqual([]);
  });

  it('menandai bagian complete, partial, dan not_found', () => {
    const statuses = sectionStatuses(sample());
    expect(statuses.identity).toEqual({ status: SECTION_STATUS.PARTIAL, notes: ['Tidak tercantum: semester.'] });
    expect(statuses.cpl.status).toBe(SECTION_STATUS.COMPLETE);
    expect(statuses.subCpmk).toEqual({ status: SECTION_STATUS.PARTIAL, notes: ['Sub-CPMK merujuk CPMK "CPMK-4" yang tidak tercantum pada RPS.'] });
    expect(statuses.weeks).toEqual({ status: SECTION_STATUS.PARTIAL, notes: ['Metode pembelajaran tidak ditemukan pada minggu 5.'] });
    expect(statuses.assessments.status).toBe(SECTION_STATUS.COMPLETE);

    const missing = sectionStatuses(incomplete());
    for (const key of ['cpl', 'subCpmk', 'assessments', 'references']) expect(missing[key]).toEqual({ status: SECTION_STATUS.NOT_FOUND, notes: [] });
    expect(missing.weeks.notes).toContain('Sub-CPMK tidak ditemukan pada minggu 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15.');
  });
});

describe('FE-08.3 tampilan hasil analisis', () => {
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
  const section = (title) => container.querySelector(`section[aria-label^="${title}:"]`);
  async function waitFor(check, label, timeout = 4000) {
    const start = Date.now();
    while (!check()) {
      if (Date.now() - start > timeout) throw new Error(`Tidak terpenuhi: ${label}. Isi: ${container.textContent.slice(0, 300)}`);
      await act(() => new Promise((r) => setTimeout(r, 20)));
    }
  }

  it('menampilkan seluruh bagian untuk RPS contoh di tab RPS Generator AI', async () => {
    localStorage.setItem(MOODLE_SESSION_KEY, JSON.stringify({ token: 'mock-3-test' }));
    await backendLogin('dosen', 'dosen123');
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={['/course/2/ai/rps']}>
          <AuthProvider><AppStateProvider><App /></AppStateProvider></AuthProvider>
        </MemoryRouter>,
      );
    });
    await waitFor(() => section('Referensi'), 'halaman hasil analisis');

    expect(section('Identitas mata kuliah').textContent).toContain('IF2105');
    expect(section('Identitas mata kuliah').textContent).toContain('3 SKS');
    expect(section('Identitas mata kuliah').textContent).toContain('Tidak tercantum');
    expect(section('CPL').textContent).toContain('CPL-1');
    // Relasi: CPMK → CPL dan Sub-CPMK → CPMK, kode tanpa sasaran ditandai.
    expect([...section('CPMK').querySelectorAll('thead th')].map((th) => th.textContent)).toEqual(['Kode', 'Deskripsi', 'CPL']);
    expect(section('CPMK').querySelector('tbody tr:nth-child(3)').textContent).toContain('CPL-1, CPL-2');
    expect(section('Sub-CPMK').textContent).toContain('CPMK-3, CPMK-4 (tidak tercantum pada RPS)');
    // Bagian lengkap tidak diberi badge; bagian yang belum lengkap diberi badge.
    expect(section('CPL').querySelector('.rounded-full, [class*="badge"]')).toBeNull();
    expect(section('Sub-CPMK').textContent).toContain('Belum lengkap');

    const table = container.querySelector('[aria-label="Tabel rencana mingguan RPS"] table');
    expect([...table.querySelectorAll('thead th')].map((th) => th.textContent)).toEqual(['Minggu', 'Sub-CPMK', 'Materi', 'Indikator', 'Metode', 'Penilaian', 'Bobot']);
    expect(table.querySelectorAll('tbody tr')).toHaveLength(16);
    expect(table.querySelector('tbody tr:nth-child(2)').textContent).toContain('5%');
    expect(table.querySelector('tbody tr:nth-child(8)').textContent).toContain('UTS');

    expect(section('Penilaian').textContent).toContain('100%');
    expect(section('Referensi').textContent).toContain('Eloquent JavaScript');
    expect(container.textContent).toContain('Catatan dari proses ekstraksi');
    expect(container.textContent).toContain('Metode pembelajaran minggu 5 tidak terbaca');
    // Tanpa emoji pada isi hasil analisis (✓ di WorkflowStepper adalah bagian lain).
    const analysisText = [...container.querySelectorAll('section[aria-label]')].map((el) => el.textContent).join(' ');
    expect(analysisText).not.toMatch(/[✓✕⚠]/);

    const planning = [...container.querySelectorAll('a')].find((a) => a.textContent === 'Lanjut ke Course Planning');
    expect(planning.getAttribute('href')).toBe('/course/2/ai/plan');
  });

  it('menandai bagian yang tidak ditemukan dengan jelas', async () => {
    root = createRoot(container);
    await act(async () => root.render(<MemoryRouter><RpsAnalysisDetails analysis={incomplete()} /></MemoryRouter>));
    for (const title of ['CPL', 'Sub-CPMK', 'Penilaian', 'Referensi']) {
      expect(section(title).getAttribute('aria-label')).toBe(`${title}: Tidak ditemukan`);
      expect(section(title).textContent).toMatch(/tidak ditemukan pada RPS\./);
    }
    expect(section('CPMK').getAttribute('aria-label')).toBe('CPMK: Lengkap');
    expect(container.textContent).toContain('Catatan dari proses ekstraksi');
    expect(container.textContent).toContain('Tabel penilaian tidak ditemukan pada dokumen.');
  });
});
