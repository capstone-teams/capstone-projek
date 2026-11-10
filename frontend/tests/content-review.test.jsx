import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CourseReviewPage from '../src/pages/dosen/ai/CourseReviewPage';
import { api } from '../src/services/apiClient';
import { contentGenerationProgressOf, groupContentsByWeek, reviewProgress, validationFindings } from '../src/utils/contentReview';

// FE-17: review konten per workflow (BE-19.2/19.3). Layanan konten diganti tiruan dengan bentuk data sesuai contoh
// OpenAPI backend (CONTENT_DETAIL_EXAMPLES).
const contents = vi.hoisted(() => ({
  listWorkflowContents: vi.fn(),
  getWorkflowContent: vi.fn(),
  listContentVersions: vi.fn(),
  approveContents: vi.fn(),
  rejectContents: vi.fn(),
  generateContents: vi.fn(),
  regenerateContents: vi.fn(),
}));
const plans = vi.hoisted(() => ({ getWorkflowPlan: vi.fn() }));
const context = vi.hoisted(() => ({ workflow: null, workflowId: 'wf-1', events: [], refresh: vi.fn() }));
vi.mock('../src/services/contentService', async (original) => ({ ...(await original()), ...contents }));
vi.mock('../src/services/coursePlanService', async (original) => ({ ...(await original()), ...plans }));
vi.mock('../src/hooks/useCourse', () => ({ useCourse: () => context }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const passed = { status: 'PASSED', score: 1, retry_count: 0 };
const failed = { status: 'FAILED', score: 0, retry_count: 1 };
const item = (id, week, kind, overrides = {}) => ({
  id, content_key: `wf-1:${week}:${kind}`, kind, week_number: week, title: `${kind} minggu ${week}`, version: 1,
  status: 'PENDING_REVIEW', revision_notes: null, validation: passed, created_at: '2026-11-10T08:00:00Z', updated_at: '2026-11-10T08:00:00Z',
  ...overrides,
});
const traceability = { week_number: 3, sub_cpmk_codes: ['Sub-CPMK-3.1'], weekly_plan_ref: 'w3' };
const details = {
  m3: { ...item('m3', 3, 'LEARNING_MATERIAL', { title: 'Normalisasi Basis Data' }), validation: { ...passed, checks: { schema: 'PASSED', sub_cpmk: 'PASSED' }, errors: null, warnings: null },
    content_data: { learning_objectives: ['Menjelaskan tujuan normalisasi'], sections: [{ heading: 'Pengantar', body_markdown: 'Normalisasi mengurangi **redundansi** data.' }], traceability } },
  r3: { ...item('r3', 3, 'RESOURCE', { title: 'Database Normalization Explained' }), validation: { ...passed, checks: { schema: 'PASSED', resource_url: 'PASSED' } },
    content_data: { url: 'https://example.com/normalization', description: 'Penjelasan bertahap 1NF-3NF.', resource_kind: 'ARTICLE', relevance_reason: 'Melengkapi materi minggu 3.', traceability } },
  a3: { ...item('a3', 3, 'ASSIGNMENT', { title: 'Normalisasi Studi Kasus' }), validation: { ...failed, checks: { schema: 'PASSED', sub_cpmk: 'FAILED' }, errors: { sub_cpmk: ['Sub-CPMK tidak ada pada weekly plan: SUB-9'] }, warnings: { style: ['Instruksi terlalu panjang.'] } },
    content_data: { instructions_markdown: 'Normalkan tabel hingga **3NF**.', expected_outputs: ['Dokumen PDF'], rubric: [{ criterion: 'Ketepatan 1NF-3NF', description: 'Tahapan benar', weight_percent: 60 }], traceability } },
  q4: { ...item('q4', 4, 'QUIZ', { title: 'Kuis Normalisasi' }), validation: passed,
    content_data: { description: 'Kuis singkat.', config: { time_limit_minutes: 15, max_attempts: 2 }, questions: [{ question_text: 'Tabel 1NF jika...', options: [{ key: 'A', text: 'Kolom atomik' }, { key: 'B', text: 'Tanpa primary key' }], correct_option_key: 'A', explanation: '1NF mensyaratkan nilai atomik.' }], traceability } },
};
const listItems = () => [
  item('m3', 3, 'LEARNING_MATERIAL', { title: 'Normalisasi Basis Data' }),
  item('r3', 3, 'RESOURCE', { title: 'Database Normalization Explained', status: 'APPROVED' }),
  item('a3', 3, 'ASSIGNMENT', { title: 'Normalisasi Studi Kasus', validation: failed }),
  item('q4', 4, 'QUIZ', { title: 'Kuis Normalisasi' }),
];

let node;
let root;
beforeEach(() => {
  vi.resetAllMocks();
  context.workflow = { id: 'wf-1', status: 'RUNNING', stage: 'instructor_review', updated_at: '2026-11-10T08:00:00Z' };
  context.workflowId = 'wf-1';
  context.events = [];
  contents.listWorkflowContents.mockResolvedValue(listItems());
  contents.getWorkflowContent.mockImplementation(async (_wf, id) => details[id] ?? { ...details.m3, id, version: 1, title: 'Versi pertama materi' });
  contents.listContentVersions.mockResolvedValue([]);
  plans.getWorkflowPlan.mockResolvedValue({ status: 'APPROVED', version: 1, weeks: [] });
  node = document.createElement('div');
  document.body.appendChild(node);
});
afterEach(async () => {
  await act(async () => root?.unmount());
  root = null;
  node.remove();
});

const settle = (ms = 0) => act(() => new Promise((resolve) => setTimeout(resolve, ms)));
async function render() {
  root ??= createRoot(node);
  await act(async () => root.render(
    <MemoryRouter initialEntries={['/course/48/ai/review']}>
      <Routes><Route path="/course/:courseId/ai/review" element={<CourseReviewPage />} /></Routes>
    </MemoryRouter>,
  ));
  await settle();
  await settle();
}
const byText = (selector, text, scope = node) => [...scope.querySelectorAll(selector)].find((el) => !el.closest('dialog') && el.textContent.trim() === text);
const row = (title) => node.querySelector(`li[aria-label="${title}"]`);
const dialog = (title) => [...document.querySelectorAll('dialog')].find((d) => d.querySelector('h2')?.textContent === title);
const fill = async (title, text) => {
  const area = dialog(title).querySelector('textarea');
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(area, text);
    area.dispatchEvent(new Event('input', { bubbles: true }));
  });
};
const submit = (title, label) => act(async () => [...dialog(title).querySelectorAll('button')].find((b) => b.textContent.trim() === label).click());
const select = async (label, value) => {
  const el = node.querySelector(`select[aria-label="${label}"]`);
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(el, value);
    el.dispatchEvent(new Event('change', { bubbles: true }));
  });
};

describe('FE-17 utilitas review konten', () => {
  it('mengelompokkan per minggu, menghitung temuan, progres, dan progres generation konten', () => {
    expect(groupContentsByWeek(listItems()).map((g) => [g.week, g.contents.length])).toEqual([[3, 3], [4, 1]]);
    expect(validationFindings(details.a3.validation)).toEqual([
      { check: 'sub_cpmk', message: 'Sub-CPMK tidak ada pada weekly plan: SUB-9', severity: 'error' },
      { check: 'style', message: 'Instruksi terlalu panjang.', severity: 'warning' },
    ]);
    expect(reviewProgress(listItems())).toEqual({ approved: 1, total: 4, complete: false });
    const running = (stage) => ({ status: 'RUNNING', stage });
    expect(contentGenerationProgressOf(running('content_generation'))).toBe('GENERATING_CONTENT');
    expect(contentGenerationProgressOf(running('validation'), [{ event: 'WORKFLOW_STAGE_STARTED', stage: 'content_generation' }, { event: 'WORKFLOW_STAGE_STARTED', stage: 'validation' }])).toBe('VALIDATING');
    expect(contentGenerationProgressOf(running('validation'), [{ event: 'WORKFLOW_STAGE_STARTED', stage: 'course_planning' }])).toBeNull();
  });

  it('regenerateContents mengirim scope dan hanya parameter scope tersebut', async () => {
    const realContents = await vi.importActual('../src/services/contentService');
    const post = vi.spyOn(api, 'post').mockResolvedValue({});
    await realContents.regenerateContents('wf', { scope: 'MINGGU', weekNumber: 3, contentId: 'x', notes: 'n' });
    await realContents.regenerateContents('wf', { scope: 'ITEM', weekNumber: 3, contentId: 'c1', notes: 'n' });
    await realContents.regenerateContents('wf', { scope: 'COURSE', notes: 'n' });
    expect(post.mock.calls).toEqual([
      ['/workflows/wf/contents/regenerate', { scope: 'MINGGU', notes: 'n', week_number: 3 }],
      ['/workflows/wf/contents/regenerate', { scope: 'ITEM', notes: 'n', content_id: 'c1' }],
      ['/workflows/wf/contents/regenerate', { scope: 'COURSE', notes: 'n' }],
    ]);
    post.mockRestore();
  });
});

describe('FE-17.1 daftar konten per minggu', () => {
  it('menampilkan konten per minggu dengan ringkasan validasi (status, skor, jumlah temuan) dan progres review', async () => {
    await render();
    expect(contents.listWorkflowContents).toHaveBeenCalledWith('wf-1');
    expect(node.querySelector('ul[aria-label="Konten Minggu 3"]').children).toHaveLength(3);
    expect(node.querySelector('ul[aria-label="Konten Minggu 4"]').children).toHaveLength(1);
    expect(row('Normalisasi Studi Kasus').textContent).toContain('Tugas');
    expect(row('Normalisasi Studi Kasus').textContent).toContain('Tidak lolos validasi');
    expect(row('Normalisasi Studi Kasus').textContent).toContain('Skor 0%');
    expect(row('Normalisasi Studi Kasus').textContent).toContain('2 temuan');
    expect(row('Normalisasi Basis Data').textContent).toContain('0 temuan');
    expect(node.querySelector('[role="progressbar"]').getAttribute('aria-valuenow')).toBe('25');
    expect(node.textContent).toContain('1/4');
  });

  it('dapat difilter berdasarkan jenis dan status', async () => {
    await render();
    await select('Filter jenis konten', 'QUIZ');
    expect(node.querySelector('ul[aria-label="Konten Minggu 3"]')).toBeNull();
    expect(row('Kuis Normalisasi')).not.toBeNull();
    await select('Filter jenis konten', '');
    await select('Filter status konten', 'APPROVED');
    expect([...node.querySelectorAll('li[aria-label]')].map((li) => li.getAttribute('aria-label'))).toEqual(['Database Normalization Explained']);
    const statusOptions = [...node.querySelector('select[aria-label="Filter status konten"]').options].map((o) => o.value);
    expect(statusOptions).toEqual(['', 'DRAFT', 'VALIDATED', 'PENDING_REVIEW', 'APPROVED', 'REJECTED', 'EXECUTED']);
  });

  it('progres review diperbarui setelah keputusan', async () => {
    contents.approveContents.mockResolvedValue({});
    await render();
    contents.listWorkflowContents.mockResolvedValue(listItems().map((i) => (i.id === 'q4' ? { ...i, status: 'APPROVED' } : i)));
    await act(async () => byText('button', 'Setujui', row('Kuis Normalisasi')).click());
    await settle();
    expect(contents.approveContents).toHaveBeenCalledWith('wf-1', ['q4']);
    expect(node.textContent).toContain('2/4');
  });
});

describe('FE-17.2 detail konten', () => {
  const open = async (title) => {
    await act(async () => byText('button', title).click());
    await settle();
  };

  it('materi: body Markdown, tujuan pembelajaran, Sub-CPMK, dan hasil validasi', async () => {
    await render();
    await open('Normalisasi Basis Data');
    const detail = node.querySelector('article[aria-label="Detail Normalisasi Basis Data"]');
    expect(detail.querySelector('.prose-moodle strong').textContent).toBe('redundansi');
    expect(detail.textContent).toContain('Menjelaskan tujuan normalisasi');
    expect(detail.textContent).toContain('Sub-CPMK: Sub-CPMK-3.1');
    expect(detail.querySelector('[aria-label="Hasil validasi"]').textContent).toContain('Lolos validasi');
  });

  it('sumber belajar: judul, tautan, deskripsi, alasan relevansi', async () => {
    await render();
    await open('Database Normalization Explained');
    const detail = node.querySelector('article[aria-label="Detail Database Normalization Explained"]');
    expect(detail.querySelector('a').getAttribute('href')).toBe('https://example.com/normalization');
    expect(detail.textContent).toContain('Penjelasan bertahap 1NF-3NF.');
    expect(detail.textContent).toContain('Alasan relevansi');
  });

  it('tugas: instruksi, luaran, rubrik, dan daftar temuan validasi', async () => {
    await render();
    await open('Normalisasi Studi Kasus');
    const detail = node.querySelector('article[aria-label="Detail Normalisasi Studi Kasus"]');
    expect(detail.textContent).toContain('Normalkan tabel hingga');
    expect(detail.textContent).toContain('Dokumen PDF');
    expect(detail.querySelector('table[aria-label="Rubrik penilaian"]').textContent).toContain('60%');
    expect(detail.querySelector('[aria-label="Temuan validasi"]').textContent).toContain('Sub-CPMK tidak ada pada weekly plan: SUB-9');
  });

  it('kuis: soal, opsi, kunci jawaban, dan pembahasan', async () => {
    await render();
    await open('Kuis Normalisasi');
    const detail = node.querySelector('article[aria-label="Detail Kuis Normalisasi"]');
    expect(detail.querySelector('[aria-label="Opsi soal 1"]').textContent).toContain('B. Tanpa primary key');
    expect(detail.textContent).toContain('Kunci jawaban: A');
    expect(detail.textContent).toContain('Pembahasan: 1NF mensyaratkan nilai atomik.');
  });

  it('riwayat versi: versi sebelumnya dapat dibuka setelah regenerasi', async () => {
    contents.listContentVersions.mockResolvedValue([{ id: 'm3', version: 2, status: 'PENDING_REVIEW' }, { id: 'm3-v1', version: 1, status: 'REJECTED' }]);
    await render();
    await open('Normalisasi Basis Data');
    expect(contents.listContentVersions).toHaveBeenCalledWith('wf-1', 'm3');
    await act(async () => byText('button', 'Versi 1').click());
    await settle();
    expect(contents.getWorkflowContent).toHaveBeenCalledWith('wf-1', 'm3-v1');
    expect(node.textContent).toContain('Menampilkan versi sebelumnya');
    expect(node.textContent).toContain('Versi pertama materi');
  });
});

describe('FE-17.3 approve, reject, dan regenerasi', () => {
  it('konten yang tidak lolos validasi tidak dapat disetujui; minggu dan semua hanya mengirim yang lolos', async () => {
    contents.approveContents.mockResolvedValue({});
    await render();
    const blocked = byText('button', 'Setujui', row('Normalisasi Studi Kasus'));
    expect(blocked.disabled).toBe(true);
    expect(blocked.title).toBe('Konten belum lolos validasi sehingga belum dapat disetujui.');
    await act(async () => byText('button', 'Setujui minggu (1)').click());
    expect(contents.approveContents).toHaveBeenLastCalledWith('wf-1', ['m3']);
    await act(async () => byText('button', 'Setujui semua yang lolos validasi (2)').click());
    expect(contents.approveContents).toHaveBeenLastCalledWith('wf-1', ['m3', 'q4']);
  });

  it('reject tanpa catatan tidak dapat dikirim; dengan catatan memanggil reject', async () => {
    contents.rejectContents.mockResolvedValue({});
    await render();
    await act(async () => byText('button', 'Tolak', row('Normalisasi Basis Data')).click());
    await submit('Tolak konten', 'Tolak konten');
    expect(dialog('Tolak konten').textContent).toContain('Catatan revisi wajib diisi.');
    expect(contents.rejectContents).not.toHaveBeenCalled();
    await fill('Tolak konten', 'Contoh kurang relevan.');
    await submit('Tolak konten', 'Tolak konten');
    expect(contents.rejectContents).toHaveBeenCalledWith('wf-1', ['m3'], 'Contoh kurang relevan.');
  });

  it('regenerasi per item dan per minggu hanya mengirim scope tersebut', async () => {
    contents.regenerateContents.mockResolvedValue({});
    await render();
    await act(async () => byText('button', 'Regenerasi', row('Kuis Normalisasi')).click());
    await fill('Regenerasi konten', 'Tambah soal analisis.');
    await submit('Regenerasi konten', 'Regenerasi');
    expect(contents.regenerateContents).toHaveBeenLastCalledWith('wf-1', { scope: 'ITEM', weekNumber: undefined, contentId: 'q4', notes: 'Tambah soal analisis.' });
    await act(async () => byText('button', 'Regenerasi minggu').click());
    expect(dialog('Regenerasi konten').textContent).toContain('Hanya minggu 3 yang dibuat ulang');
    await fill('Regenerasi konten', 'Perbaiki minggu 3.');
    await submit('Regenerasi konten', 'Regenerasi');
    expect(contents.regenerateContents).toHaveBeenLastCalledWith('wf-1', { scope: 'MINGGU', weekNumber: 3, contentId: undefined, notes: 'Perbaiki minggu 3.' });
  });

  it('regenerasi seluruh konten (COURSE) meminta konfirmasi dan catatan', async () => {
    contents.regenerateContents.mockResolvedValue({});
    await render();
    await act(async () => byText('button', 'Regenerasi seluruh konten').click());
    const confirm = dialog('Regenerasi seluruh konten');
    expect(confirm.textContent).toContain('Seluruh konten kursus akan dibuat ulang');
    await submit('Regenerasi seluruh konten', 'Ya, regenerasi seluruh konten');
    expect(contents.regenerateContents).not.toHaveBeenCalled();
    await fill('Regenerasi seluruh konten', 'Sesuaikan dengan RPS terbaru.');
    await submit('Regenerasi seluruh konten', 'Ya, regenerasi seluruh konten');
    expect(contents.regenerateContents).toHaveBeenCalledWith('wf-1', { scope: 'COURSE', weekNumber: undefined, contentId: undefined, notes: 'Sesuaikan dengan RPS terbaru.' });
  });

  it('seluruh konten disetujui menampilkan langkah berikutnya ke eksekusi FULL', async () => {
    contents.listWorkflowContents.mockResolvedValue(listItems().map((i) => ({ ...i, status: 'APPROVED', validation: passed })));
    await render();
    const next = byText('a', 'Lanjut ke eksekusi FULL');
    expect(next.getAttribute('href')).toBe('/course/48/ai/publish');
  });
});

describe('FE-17 generate konten', () => {
  it('tanpa konten dan course plan disetujui: Generate konten memanggil POST /contents/generate', async () => {
    contents.listWorkflowContents.mockResolvedValue([]);
    contents.generateContents.mockResolvedValue({ workflow_id: 'wf-1', status: 'RUNNING' });
    await render();
    await act(async () => byText('button', 'Generate konten').click());
    expect(contents.generateContents).toHaveBeenCalledWith('wf-1');
    expect(context.refresh).toHaveBeenCalled();
  });

  it('course plan belum disetujui: konten belum dapat dibuat', async () => {
    contents.listWorkflowContents.mockResolvedValue([]);
    plans.getWorkflowPlan.mockResolvedValue({ status: 'DRAFT' });
    await render();
    expect(byText('button', 'Generate konten')).toBeUndefined();
    expect(node.textContent).toContain('Konten dibuat setelah course plan disetujui.');
  });

  it('saat agent membuat konten menampilkan progres, bukan tombol generate', async () => {
    contents.listWorkflowContents.mockResolvedValue([]);
    context.workflow = { id: 'wf-1', status: 'RUNNING', stage: 'content_generation', updated_at: '2026-11-10T08:00:00Z' };
    await render();
    expect(node.textContent).toContain('Agent sedang membuat konten mingguan');
    expect(byText('button', 'Generate konten')).toBeUndefined();
  });
});
