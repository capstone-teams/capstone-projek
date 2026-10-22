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
import { getCourseContents } from '../src/services/moodle/moodleApi';
import { CM_ACTION, SECTION_ACTION, createActivity, moveActivity, renameActivity, renameSection, updateCourseState } from '../src/services/moodle/courseEditing';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// Mock Moodle: 3 = dosen (editingteacher kursus 2 & 4, non-editing teacher kursus 3), 5 = mahasiswa.
const TOKENS = { dosen: 'mock-3-test', mahasiswa: 'mock-5-test' };
const findCm = (sections, name) => sections.flatMap((s) => s.modules).find((m) => m.name === name);

beforeAll(() => configureMock({ latencyMs: 0, stepMs: 5 }));
beforeEach(() => {
  resetMockDb();
  resetMockMoodle();
  localStorage.clear();
});

describe('Edit mode: service dan mock Moodle', () => {
  const as = (who) => setMoodleToken(TOKENS[who]);
  afterEach(() => setMoodleToken(null));

  it('menyembunyikan aktivitas dan section dari mahasiswa, lalu menampilkannya lagi', async () => {
    as('dosen');
    const sections = await getCourseContents(2);
    const quiz = findCm(sections, 'Kuis 3');
    await updateCourseState(2, CM_ACTION.HIDE, [quiz.id]);
    await updateCourseState(2, SECTION_ACTION.HIDE, [sections[1].id]);
    expect(findCm(await getCourseContents(2), 'Kuis 3').visible).toBe(0);

    as('mahasiswa');
    const studentView = await getCourseContents(2);
    expect(findCm(studentView, 'Kuis 3').uservisible).toBe(false);
    expect(studentView[1].uservisible).toBe(false);

    as('dosen');
    await updateCourseState(2, CM_ACTION.SHOW, [quiz.id]);
    as('mahasiswa');
    expect(findCm(await getCourseContents(2), 'Kuis 3').uservisible).toBe(true);
  });

  it('menduplikat, menggeser, memindahkan, mengganti nama, dan menghapus aktivitas', async () => {
    as('dosen');
    let sections = await getCourseContents(2);
    const quiz = findCm(sections, 'Kuis 3');
    await updateCourseState(2, CM_ACTION.DUPLICATE, [quiz.id]);
    await updateCourseState(2, CM_ACTION.INDENT, [quiz.id]);
    sections = await getCourseContents(2);
    expect(findCm(sections, 'Kuis 3 (copy)')).toBeTruthy();
    expect(findCm(sections, 'Kuis 3').indent).toBe(1);

    const general = sections[0];
    await moveActivity(2, quiz.id, general.id, general.modules[0].id);
    await renameActivity(quiz.id, 'Kuis Tengah Semester');
    await renameSection('topics', general.id, 'Informasi Umum');
    sections = await getCourseContents(2);
    expect(sections[0].name).toBe('Informasi Umum');
    expect(sections[0].modules[0].name).toBe('Kuis Tengah Semester');

    await updateCourseState(2, CM_ACTION.DELETE, [quiz.id]);
    expect(findCm(await getCourseContents(2), 'Kuis Tengah Semester')).toBeUndefined();
  });

  it('menolak perubahan dari non-editing teacher dan menolak menyembunyikan section umum', async () => {
    as('dosen');
    const basisData = await getCourseContents(3);
    await expect(updateCourseState(3, CM_ACTION.HIDE, [basisData[1].modules[0].id])).rejects.toMatchObject({ code: 'nopermissions' });
    const web = await getCourseContents(2);
    await expect(updateCourseState(2, SECTION_ACTION.HIDE, [web[0].id])).rejects.toMatchObject({ code: 'cannothidesection' });
    await expect(renameActivity(web[1].modules[0].id, '   ')).rejects.toMatchObject({ code: 'invalidparameter' });
  });

  it('membuat tugas dan teks dan media; menolak input atau izin yang tidak valid', async () => {
    as('dosen');
    const { cmid } = await createActivity(2, 1, 'assign', { name: 'Tugas Baru', intro: '<p>Kerjakan.</p>', allowsubmissionsfromdate: 1000, duedate: 2000, grade: 80 });
    await createActivity(2, 1, 'label', { text: 'Baris satu\nbaris dua' });
    const week1 = (await getCourseContents(2))[1];
    expect(week1.modules.at(-2)).toMatchObject({ id: cmid, modname: 'assign', name: 'Tugas Baru', dates: [{ label: 'Opened:', timestamp: 1000 }, { label: 'Due:', timestamp: 2000 }] });
    expect(week1.modules.at(-1)).toMatchObject({ modname: 'label', name: 'Baris satu baris dua', description: '<p>Baris satu<br>baris dua</p>' });

    await expect(createActivity(2, 1, 'assign', { name: '  ' })).rejects.toMatchObject({ code: 'invalidparameter' });
    await expect(createActivity(2, 1, 'assign', { name: 'X', allowsubmissionsfromdate: 2000, duedate: 1000 })).rejects.toMatchObject({ message: 'Tenggat harus setelah tanggal dibuka.' });
    await expect(createActivity(2, 1, 'label', { text: '' })).rejects.toMatchObject({ code: 'invalidparameter' });
    await expect(createActivity(3, 1, 'assign', { name: 'X' })).rejects.toMatchObject({ code: 'nopermissions' });
  });

  it('menambah section baru di akhir kursus', async () => {
    as('dosen');
    const before = await getCourseContents(4);
    await updateCourseState(4, SECTION_ACTION.ADD);
    const after = await getCourseContents(4);
    expect(after).toHaveLength(before.length + 1);
    expect(after.at(-1)).toMatchObject({ name: 'New section', section: before.length, modules: [] });
  });

  it('kembali ke isi awal setelah resetMockMoodle()', async () => {
    as('dosen');
    const sections = await getCourseContents(2);
    await updateCourseState(2, CM_ACTION.DELETE, [findCm(sections, 'Kuis 3').id]);
    resetMockMoodle();
    expect(findCm(await getCourseContents(2), 'Kuis 3')).toBeTruthy();
  });
});

describe('Edit mode: halaman kursus', () => {
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

  async function render(path, who = 'dosen') {
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
      if (Date.now() - start > timeout) throw new Error(`Tidak terpenuhi: ${label}. Isi: ${container.textContent.slice(0, 300)}`);
      await act(() => new Promise((r) => setTimeout(r, 20)));
    }
  }
  const waitForText = (text) => waitFor(() => container.textContent.includes(text), text);
  const q = (selector) => container.querySelector(selector);
  const button = (text) => [...container.querySelectorAll('button')].find((b) => b.textContent.trim() === text);
  const click = (el) => act(async () => el.click());
  function type(input, value) {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }
  const toggle = () => q('[role="switch"]');
  async function openEditMode() {
    await render('/course/2');
    await waitFor(() => toggle(), 'saklar Mode edit');
    await click(toggle());
    await waitFor(() => q('[aria-label="Aksi untuk Kuis 3"]'), 'menu aktivitas');
  }
  async function chooseAction(activity, label) {
    await click(q(`[aria-label="Aksi untuk ${activity}"]`));
    await click([...container.querySelectorAll('[role="menuitem"]')].find((item) => item.textContent.startsWith(label)));
  }

  it('saklar Mode edit hanya muncul untuk pengajar yang boleh mengubah kursus', async () => {
    await render('/course/2');
    await waitFor(() => toggle(), 'saklar pada kursus 2');
    expect(toggle().getAttribute('aria-checked')).toBe('false');
    expect(q('[aria-label="Aksi untuk Kuis 3"]')).toBeNull();
    act(() => root.unmount());

    // Non-editing teacher pada kursus 3.
    root = null;
    await render('/course/3');
    await waitForText('Pengantar Basis Data');
    expect(toggle()).toBeNull();
  });

  it('mahasiswa tidak melihat saklar Mode edit', async () => {
    await render('/course/2', 'mahasiswa');
    await waitForText('Pengantar Pemrograman Web');
    expect(toggle()).toBeNull();
  });

  it('menampilkan kontrol edit dan mengingat pilihan Mode edit', async () => {
    await openEditMode();
    expect(toggle().getAttribute('aria-checked')).toBe('true');
    expect(q('[aria-label="Ubah nama Kuis 3"]')).not.toBeNull();
    expect(q('[aria-label="Aksi untuk section General"]')).not.toBeNull();
    expect(container.textContent).toContain('Tambah aktivitas atau sumber');
    expect(button('+ Tambah section')).toBeTruthy();
    expect(Object.values({ ...localStorage }).some((value) => value.includes('"course.editMode":true'))).toBe(true);
  });

  it('menu aktivitas berisi aksi edit seperti Moodle', async () => {
    await openEditMode();
    await click(q('[aria-label="Aksi untuk Kuis 3"]'));
    const labels = [...container.querySelectorAll('[role="menuitem"]')].map((item) => item.textContent.replace('(dibuka di Moodle, tab baru)', '').replace('↗', '').trim());
    expect(labels).toEqual(['Edit pengaturan', 'Pindahkan', 'Geser ke kanan', 'Sembunyikan', 'Duplikat', 'Atur peran', 'Hapus']);
    expect(q('a[role="menuitem"]').getAttribute('href')).toMatch(/\/course\/modedit\.php\?update=\d+$/);
  });

  async function openChooser(sectionNumber = 0) {
    await openEditMode();
    await click([...container.querySelectorAll(`#section-${sectionNumber} button`)].find((b) => b.textContent.includes('Tambah aktivitas atau sumber')));
  }
  const dialog = () => q('dialog');
  const chooseType = (label) => click([...dialog().querySelectorAll('[aria-label="Jenis aktivitas"] button')].find((b) => b.textContent.startsWith(label)));
  function fill(field, value) {
    const proto = field.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(field, value);
    field.dispatchEvent(new Event('input', { bubbles: true }));
  }
  const inputByLabel = (text) => [...dialog().querySelectorAll('label')].find((l) => l.textContent.startsWith(text)).querySelector('input, textarea');

  it('pemilih aktivitas menampilkan Tugas serta Teks dan media untuk section tersebut', async () => {
    await openChooser();
    expect(container.textContent).toContain('Tambah aktivitas atau sumber ke "General"');
    const types = [...dialog().querySelectorAll('[aria-label="Jenis aktivitas"] button .font-semibold')].map((el) => el.textContent);
    expect(types).toEqual(['Tugas', 'Teks dan media']);
  });

  it('membuat tugas lewat formulir dengan validasi', async () => {
    await openChooser(1);
    await chooseType('Tugas');
    expect(dialog().textContent).toContain('Tambah Tugas ke "Minggu 1: Pengantar Pemrograman Web"');
    expect(inputByLabel('Nama tugas').closest('label').textContent).toContain('(wajib diisi)');

    await act(async () => dialog().querySelector('form').requestSubmit());
    expect(dialog().textContent).toContain('Nama tugas wajib diisi.');
    expect(inputByLabel('Nama tugas').getAttribute('aria-invalid')).toBe('true');

    await act(async () => {
      fill(inputByLabel('Nama tugas'), 'Tugas Pengantar');
      fill(inputByLabel('Deskripsi'), 'Buat ringkasan <HTTP>.');
      fill(inputByLabel('Dibuka'), '2026-10-25T08:00');
      fill(inputByLabel('Tenggat'), '2026-10-24T08:00');
    });
    await act(async () => dialog().querySelector('form').requestSubmit());
    expect(dialog().textContent).toContain('Tenggat harus setelah tanggal dibuka.');
    expect(dialog().textContent).not.toContain('Nama tugas wajib diisi.');

    await act(async () => fill(inputByLabel('Tenggat'), '2026-11-01T23:59'));
    await act(async () => dialog().querySelector('form').requestSubmit());
    await waitFor(() => q('#section-1 [aria-label="Aksi untuk Tugas Pengantar"]'), 'tugas baru di Minggu 1');
    expect(q('dialog')).toBeNull();
    expect(container.textContent).toContain('Tugas ditambahkan.');
    const row = q('#section-1 [aria-label="Aksi untuk Tugas Pengantar"]').closest('li');
    expect(row.textContent).toContain('Dibuka:');
    expect(row.textContent).toContain('Tenggat:');
  });

  it('membuat teks dan media; isi wajib diisi dan HTML tidak dijalankan', async () => {
    await openChooser();
    await chooseType('Teks dan media');
    await act(async () => dialog().querySelector('form').requestSubmit());
    expect(dialog().textContent).toContain('Isi teks wajib diisi.');
    await act(async () => fill(inputByLabel('Isi'), 'Selamat datang di kelas.\n\n<b>Jadwal</b> kuliah Senin.'));
    await act(async () => dialog().querySelector('form').requestSubmit());
    await waitFor(() => container.textContent.includes('Teks dan media ditambahkan.'), 'toast');
    const general = q('#section-0');
    expect(general.textContent).toContain('Selamat datang di kelas.');
    expect(general.textContent).toContain('<b>Jadwal</b> kuliah Senin.');
    expect(general.querySelector('b')).toBeNull();
  });

  it('kembali ke pilihan jenis tanpa menyimpan apa pun', async () => {
    await openChooser();
    await chooseType('Tugas');
    await act(async () => fill(inputByLabel('Nama tugas'), 'Draf'));
    await click(button('← Pilih jenis lain'));
    expect(dialog().querySelector('[aria-label="Jenis aktivitas"]')).not.toBeNull();
    expect(container.textContent).not.toContain('Tugas ditambahkan.');
    expect(findCm(await getCourseContents(2), 'Draf')).toBeUndefined();
  });

  it('menyembunyikan aktivitas dan menampilkan badge', async () => {
    await openEditMode();
    await chooseAction('Kuis 3', 'Sembunyikan');
    await waitForText('Disembunyikan dari mahasiswa');
    await chooseAction('Kuis 3', 'Tampilkan');
    await waitFor(() => !container.textContent.includes('Disembunyikan dari mahasiswa'), 'badge hilang');
  });

  it('mengganti nama aktivitas dengan pensil; Escape membatalkan', async () => {
    await openEditMode();
    await click(q('[aria-label="Ubah nama Kuis 3"]'));
    let input = q('input[aria-label="Nama baru untuk Kuis 3"]');
    await act(async () => type(input, 'Batal diganti'));
    await act(async () => input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })));
    expect(q('input[aria-label="Nama baru untuk Kuis 3"]')).toBeNull();
    expect(container.textContent).not.toContain('Batal diganti');

    await click(q('[aria-label="Ubah nama Kuis 3"]'));
    input = q('input[aria-label="Nama baru untuk Kuis 3"]');
    await act(async () => type(input, 'Kuis Minggu 3'));
    await act(async () => input.form.requestSubmit());
    await waitFor(() => q('[aria-label="Aksi untuk Kuis Minggu 3"]'), 'nama baru tampil');
  });

  it('menghapus aktivitas setelah konfirmasi', async () => {
    await openEditMode();
    await chooseAction('Kuis 3', 'Hapus');
    expect(container.textContent).toContain('Hapus aktivitas?');
    await click(button('Hapus'));
    await waitFor(() => !q('[aria-label="Aksi untuk Kuis 3"]'), 'aktivitas terhapus');
    expect(container.textContent).toContain('Aktivitas dihapus.');
  });

  it('memindahkan aktivitas ke section lain', async () => {
    await openEditMode();
    await chooseAction('Kuis 3', 'Pindahkan');
    const select = q('dialog select');
    await act(async () => {
      select.value = '200';
      select.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await click(button('Pindahkan'));
    await waitFor(() => q('#section-0 [aria-label="Aksi untuk Kuis 3"]'), 'Kuis 3 pindah ke General');
  });

  it('section umum tidak menawarkan aksi sembunyikan', async () => {
    await openEditMode();
    await click(q('[aria-label="Aksi untuk section General"]'));
    const general = [...container.querySelectorAll('[role="menuitem"]')].map((item) => item.textContent);
    expect(general.some((text) => text.includes('Sembunyikan section'))).toBe(false);
    await click(q('[aria-label="Aksi untuk section Minggu 1: Pengantar Pemrograman Web"]'));
    const week = [...container.querySelectorAll('[role="menuitem"]')].map((item) => item.textContent);
    expect(week).toContain('Sembunyikan section');
  });

  it('menampilkan error Moodle dan tetap di Edit mode', async () => {
    await openEditMode();
    // Aktivitas sudah dihapus dari tempat lain (mis. tab Moodle) sebelum dosen menekan Sembunyikan.
    const quiz = findCm(await getCourseContents(2), 'Kuis 3');
    await updateCourseState(2, CM_ACTION.DELETE, [quiz.id]);
    await chooseAction('Kuis 3', 'Sembunyikan');
    await waitFor(() => q('[role="alert"]'), 'pesan error');
    expect(q('[role="alert"]').textContent).toContain('Aktivitas tidak ditemukan.');
    expect(toggle().getAttribute('aria-checked')).toBe('true');
    // Tampilan disegarkan mengikuti Moodle: aktivitas yang sudah dihapus tidak lagi tampil.
    await waitFor(() => !q('[aria-label="Aksi untuk Kuis 3"]'), 'daftar disegarkan');
  });
});
