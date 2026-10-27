import { afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../src/context/AuthProvider';
import { AppStateProvider } from '../src/context/AppStateProvider';
import App from '../src/App';
import { MOODLE_SESSION_KEY } from '../src/services/config';
import { login as backendLogin } from '../src/services/authService';
import { configureMock, resetMockDb } from '../src/services/mock/mockServer';
import { resetMockMoodle } from '../src/services/mock/mockMoodle';
import { setMoodleToken } from '../src/services/moodle/moodleClient';
import { getAssignments, getSubmissionStatus, saveSubmission } from '../src/services/moodle/moodleApi';
import { createActivity } from '../src/services/moodle/courseEditing';
import { countWords, submissionContent, submissionTypes } from '../src/utils/assignSubmission';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// Mock Moodle: 3 = dosen (editingteacher kursus 2), 5 = mahasiswa kursus 2.
const TOKENS = { dosen: 'mock-3-test', mahasiswa: 'mock-5-test' };
const MB = 1024 * 1024;
const file = (name, size) => new File([new Uint8Array(size)], name);
const entry = (f, filepath = '/') => ({ filepath, filename: f.name, filesize: f.size, file: f });
const findAssign = async (name) => (await getAssignments([2])).find((a) => a.name === name);

beforeAll(() => configureMock({ latencyMs: 0, stepMs: 5 }));
beforeEach(() => {
  resetMockDb();
  resetMockMoodle();
  localStorage.clear();
});

describe('Pengumpulan tugas: service dan mock Moodle', () => {
  it('membaca jenis pengumpulan dari configs tugas', async () => {
    setMoodleToken(TOKENS.mahasiswa);
    expect(submissionTypes(await findAssign('Tugas 4: JavaScript Dasar'))).toEqual({ onlineText: true, wordLimit: 0, files: true, maxFiles: 20, maxBytes: MB });

    setMoodleToken(TOKENS.dosen);
    await createActivity(2, 1, 'assign', { name: 'Esai', onlinetext_enabled: 1, onlinetext_wordlimit: 50, file_enabled: 0, file_maxfiles: 3, file_maxbytes: 2 * MB });
    expect(submissionTypes(await findAssign('Esai'))).toMatchObject({ onlineText: true, wordLimit: 50, files: false });
  });

  it('menyimpan teks online dan file, lalu mempertahankan file bila tidak diunggah ulang', async () => {
    setMoodleToken(TOKENS.mahasiswa);
    const assign = await findAssign('Tugas 4: JavaScript Dasar');
    await saveSubmission(assign.id, {
      onlineText: '<p>Jawaban pertama</p>',
      files: [entry(file('laporan.pdf', 2048)), entry(file('data.csv', 10), '/lampiran/')],
    });
    let { submission } = (await getSubmissionStatus(assign.id)).lastattempt;
    expect(submission.status).toBe('submitted');
    expect(submissionContent(submission)).toMatchObject({
      text: '<p>Jawaban pertama</p>',
      files: [{ filename: 'laporan.pdf', filepath: '/', filesize: 2048 }, { filename: 'data.csv', filepath: '/lampiran/' }],
    });

    // null: file tidak diubah (files_filemanager tidak dikirim).
    await saveSubmission(assign.id, { onlineText: '<p>Jawaban revisi</p>', files: null });
    ({ submission } = (await getSubmissionStatus(assign.id)).lastattempt);
    expect(submissionContent(submission)).toMatchObject({ text: '<p>Jawaban revisi</p>', files: [{ filename: 'laporan.pdf' }, { filename: 'data.csv' }] });

    // File lama tanpa objek File ikut ke draft baru; array kosong mengosongkan area file.
    const [kept] = submissionContent(submission).files;
    await saveSubmission(assign.id, { onlineText: null, files: [kept] });
    ({ submission } = (await getSubmissionStatus(assign.id)).lastattempt);
    expect(submissionContent(submission).files.map((f) => f.filename)).toEqual(['laporan.pdf']);
    await saveSubmission(assign.id, { onlineText: null, files: [] });
    ({ submission } = (await getSubmissionStatus(assign.id)).lastattempt);
    expect(submissionContent(submission)).toMatchObject({ text: '<p>Jawaban revisi</p>', files: [] });
  });

  it('menolak batas kata, ukuran file, tugas yang belum dibuka, dan pengajar', async () => {
    setMoodleToken(TOKENS.dosen);
    await createActivity(2, 1, 'assign', { name: 'Esai Singkat', onlinetext_enabled: 1, onlinetext_wordlimit: 3 });
    setMoodleToken(TOKENS.mahasiswa);
    const essay = await findAssign('Esai Singkat');
    await expect(saveSubmission(essay.id, { onlineText: '<p>satu dua tiga empat</p>' })).rejects.toMatchObject({ code: 'couldnotsavesubmission' });
    await expect(saveSubmission(essay.id, { files: [entry(file('besar.zip', 2 * MB))] })).rejects.toMatchObject({ code: 'couldnotsavesubmission' });
    await expect(saveSubmission((await findAssign('Tugas 6: REST API dan JSON')).id, { onlineText: 'x' })).rejects.toMatchObject({ code: 'couldnotsavesubmission' });

    setMoodleToken(TOKENS.dosen);
    await expect(saveSubmission(essay.id, { onlineText: 'x' })).rejects.toMatchObject({ code: 'nopermissions' });
  });

  it('menghitung kata tanpa tag HTML', () => {
    expect(countWords('<p>Halo dunia</p><p>ini   Moodle</p>')).toBe(4);
    expect(countWords('   ')).toBe(0);
  });
});

describe('Pengumpulan tugas: halaman mahasiswa', () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
  });
  afterEach(() => {
    act(() => root?.unmount());
    root = null;
    container.remove();
  });

  async function render(path, who = 'mahasiswa') {
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
  async function waitFor(check, label, timeout = 3000) {
    const start = Date.now();
    while (!check()) {
      if (Date.now() - start > timeout) throw new Error(`Tidak terpenuhi: ${label}. Isi: ${container.textContent.slice(-400)}`);
      await act(() => new Promise((r) => setTimeout(r, 20)));
    }
  }
  const button = (text) => [...container.querySelectorAll('button')].find((b) => b.textContent.trim() === text);
  const click = (el) => act(async () => el.click());
  function pick(input, files) {
    Object.defineProperty(input, 'files', { value: files, configurable: true });
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }
  async function openAssign(name) {
    setMoodleToken(TOKENS.mahasiswa);
    const assign = await findAssign(name);
    await render(`/course/2/mod/${assign.cmid}`);
    await waitFor(() => container.textContent.includes('Grading status'), 'status pengumpulan');
    return assign;
  }

  const link = (text) => [...container.querySelectorAll('a')].find((a) => a.textContent.trim() === text);
  const editor = () => container.querySelector('[role="textbox"][contenteditable]');
  const dialogButton = (text) => [...container.querySelectorAll('dialog button')].find((b) => b.textContent === text);
  async function type(html) {
    await act(async () => {
      editor().innerHTML = html;
      editor().dispatchEvent(new Event('input', { bubbles: true }));
    });
  }
  async function openEditPage(name) {
    await openAssign(name);
    await waitFor(() => link('Add submission'), 'tombol Add submission');
    await click(link('Add submission'));
    await waitFor(() => editor(), 'halaman Edit submission');
  }

  it('halaman Edit submission meniru Moodle: editor, file manager, simpan', async () => {
    await openEditPage('Tugas 4: JavaScript Dasar');
    expect(container.querySelector('[aria-label="Breadcrumb aktivitas"]').textContent).toContain('Tugas 4: JavaScript Dasar / Edit submission');
    expect(container.textContent).toContain('Opened:');
    expect(container.textContent).toContain('Due:');
    expect(button('Add submission').getAttribute('aria-expanded')).toBe('true');
    // Menu bar dan toolbar editor seperti TinyMCE.
    expect([...container.querySelectorAll('[role="menubar"] > div > button')].map((b) => b.textContent)).toEqual(['Edit', 'View', 'Insert', 'Format', 'Tools', 'Table', 'Help']);
    for (const label of ['Undo', 'Redo', 'Bold', 'Italic', 'Image', 'Multimedia', 'Link', 'Unlink', 'Full screen']) {
      expect(container.querySelector(`[role="toolbar"] [aria-label="${label}"]`)).not.toBeNull();
    }
    expect(container.textContent).toContain('0 words');
    expect(container.textContent).toContain('Maximum file size: 1 MB, maximum number of files: 20');
    expect(container.textContent).toContain('You can drag and drop files here to add them.');

    await type('<p>Jawaban <strong>saya</strong> di sini</p>');
    expect(container.textContent).toContain('4 words');

    const input = container.querySelector('input[type="file"]');
    await act(async () => pick(input, [file('terlalu-besar.zip', 2 * MB)]));
    expect(container.textContent).toContain('The file terlalu-besar.zip is too large. The maximum size you can upload is 1 MB.');
    await act(async () => pick(input, [file('laporan.pdf', 1500), file('laporan.pdf', 900)]));
    expect(container.textContent).toContain('laporan (1).pdf');
    expect(container.querySelector('[role="alert"]')).toBeNull();

    // Folder baru lalu file di dalamnya; tampilan detail.
    await click(container.querySelector('[aria-label="Create folder"]'));
    await act(async () => {
      const name = [...container.querySelectorAll('dialog label')].find((l) => l.textContent.startsWith('New folder name')).querySelector('input');
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(name, 'lampiran');
      name.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await click(dialogButton('Create folder'));
    await click(container.querySelector('[aria-label="Display folder with file details"]'));
    const table = () => [...container.querySelectorAll('table')].find((t) => t.textContent.includes('Last modified'));
    expect(table().textContent).toContain('Folder');
    await click([...table().querySelectorAll('button')].find((b) => b.textContent === 'lampiran'));
    expect(container.querySelector('[aria-label="Jalur folder"]').textContent).toContain('lampiran');
    await act(async () => pick(input, [file('data.csv', 10)]));

    await click(button('Save changes'));
    await waitFor(() => link('Edit submission'), 'kembali ke halaman tugas');
    expect(container.textContent).toContain('Submitted for grading');
    expect(container.textContent).toContain('Changes saved');
    expect(container.querySelector('td strong').textContent).toBe('saya');
    expect(container.textContent).toContain('laporan (1).pdf');
    expect(container.textContent).toContain('data.csv (lampiran)');
  });

  it('mengubah pengumpulan: isi lama dimuat dan file dapat dihapus', async () => {
    setMoodleToken(TOKENS.mahasiswa);
    const assign = await findAssign('Tugas 4: JavaScript Dasar');
    await saveSubmission(assign.id, { onlineText: '<p>Draf awal</p>', files: [entry(file('lama.pdf', 100))] });
    await openAssign('Tugas 4: JavaScript Dasar');
    await click(link('Edit submission'));
    await waitFor(() => editor(), 'halaman Edit submission');
    expect(editor().innerHTML).toBe('<p>Draf awal</p>');
    expect(container.textContent).toContain('2 words');
    await click([...container.querySelectorAll('button')].find((b) => b.textContent.endsWith('lama.pdf')));
    await click(dialogButton('Delete'));
    expect(container.textContent).toContain('You can drag and drop files here to add them.');
    await click(button('Save changes'));
    await waitFor(() => link('Add submission') || link('Edit submission'), 'kembali ke halaman tugas');
    expect(submissionContent((await getSubmissionStatus(assign.id)).lastattempt.submission).files).toEqual([]);
  });

  it('menolak simpan saat batas kata terlampaui dengan pesan Moodle', async () => {
    setMoodleToken(TOKENS.dosen);
    await createActivity(2, 1, 'assign', { name: 'Esai Singkat', onlinetext_enabled: 1, onlinetext_wordlimit: 3, file_enabled: 0 });
    await openEditPage('Esai Singkat');
    expect(container.querySelector('input[type="file"]')).toBeNull();
    await type('<p>satu dua tiga empat</p>');
    await click(button('Save changes'));
    expect(container.textContent).toContain('The word limit for this assignment is 3 words and you are attempting to submit 4 words.');
    expect(editor().getAttribute('aria-invalid')).toBe('true');
  });

  it('tugas yang belum dibuka tidak menampilkan tombol pengumpulan', async () => {
    await openAssign('Tugas 6: REST API dan JSON');
    expect(link('Add submission')).toBeUndefined();
    expect(container.textContent).toContain('This assignment will accept submissions from');
  });
});
