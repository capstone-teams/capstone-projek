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
import { getAssignments, getCourseContents } from '../src/services/moodle/moodleApi';
import { submissionTypes } from '../src/utils/assignSubmission';
import { CM_ACTION, SECTION_ACTION, createActivity, moveActivity, renameActivity, renameSection, updateCourseState } from '../src/services/moodle/courseEditing';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// Mock Moodle: 3 = dosen (editingteacher kursus 2 & 4, non-editing teacher kursus 3), 5 = mahasiswa.
const TOKENS = { dosen: 'mock-3-test', mahasiswa: 'mock-5-test' };
const findCm = (sections, name) => sections.flatMap((s) => s.modules).find((m) => m.name === name);

beforeAll(() => {
  configureMock({ latencyMs: 0, stepMs: 5 });
  // jsdom tidak mengimplementasikan scrollIntoView (dipakai saat membuka #section-n).
  Element.prototype.scrollIntoView ??= () => {};
});
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

    await createActivity(2, 1, 'quiz', { name: 'Kuis Baru', intro: '', timeopen: 1000, timeclose: 2000 });
    expect((await getCourseContents(2))[1].modules.at(-1)).toMatchObject({ modname: 'quiz', name: 'Kuis Baru', dates: [{ label: 'Opened:', timestamp: 1000 }, { label: 'Closes:', timestamp: 2000 }] });
    await expect(createActivity(2, 1, 'quiz', { name: ' ' })).rejects.toMatchObject({ code: 'invalidparameter' });
    await expect(createActivity(2, 1, 'quiz', { name: 'X', timeopen: 2000, timeclose: 1000 })).rejects.toMatchObject({ message: 'Waktu ditutup harus setelah waktu dibuka.' });
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
  // Pengajar yang boleh mengubah kursus langsung masuk mode edit saat membuka kursus.
  async function openEditMode() {
    await render('/course/2');
    await waitFor(() => q('[aria-label="Aksi untuk Kuis 3"]'), 'menu aktivitas');
  }
  async function chooseAction(activity, label) {
    await click(q(`[aria-label="Aksi untuk ${activity}"]`));
    await click([...container.querySelectorAll('[role="menuitem"]')].find((item) => item.textContent.startsWith(label)));
  }

  it('pengajar yang boleh mengubah kursus selalu melihat kontrol edit tanpa saklar', async () => {
    await openEditMode();
    expect(q('[role="switch"]')).toBeNull();
    expect(q('[aria-label="Ubah nama Kuis 3"]')).not.toBeNull();
    expect(q('[aria-label="Aksi untuk section General"]')).not.toBeNull();
    expect(container.textContent).toContain('Tambah aktivitas atau sumber');
    expect(button('+ Tambah section')).toBeTruthy();
  });

  it('non-editing teacher dan mahasiswa tidak mendapat kontrol edit', async () => {
    await render('/course/3');
    await waitForText('Pengantar Basis Data');
    expect(q('[aria-label^="Aksi untuk"]')).toBeNull();
    act(() => root.unmount());

    root = null;
    await render('/course/2', 'mahasiswa');
    await waitForText('Pengantar Pemrograman Web');
    expect(q('[aria-label^="Aksi untuk"]')).toBeNull();
    expect(container.textContent).not.toContain('Tambah aktivitas atau sumber');
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
    await openAdd(sectionNumber);
  }
  const dialog = () => q('dialog');
  const tiles = () => [...dialog().querySelectorAll('ul[aria-label="Activities and resources"] > li > button')];
  const tileNames = () => tiles().map((b) => b.textContent);
  const chooseType = (name) => click(tiles().find((b) => b.textContent === name));
  const openAdd = (sectionNumber = 0) =>
    click([...container.querySelectorAll(`#section-${sectionNumber} button`)].find((b) => b.textContent.includes('Tambah aktivitas atau sumber')));
  const tab = (name) => click([...dialog().querySelectorAll('[role="tab"]')].find((b) => b.textContent === name));
  function fill(field, value) {
    const proto = field.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(field, value);
    field.dispatchEvent(new Event('input', { bubbles: true }));
  }

  it('pemilih aktivitas meniru dialog Moodle: pencarian, tab, dan tiga jenis', async () => {
    await openChooser();
    expect(dialog().querySelector('h2').textContent).toBe('Add an activity or resource');
    expect([...dialog().querySelectorAll('[role="tab"]')].map((b) => b.textContent)).toEqual(['Starred', 'All', 'Activities', 'Resources', 'Recommended']);
    expect(tileNames()).toEqual(['Assignment', 'Quiz', 'Text and media area']);
    await tab('Activities');
    expect(tileNames()).toEqual(['Assignment', 'Quiz']);
    await tab('Resources');
    expect(tileNames()).toEqual(['Text and media area']);
    await tab('Recommended');
    expect(tileNames()).toEqual(['Assignment', 'Quiz', 'Text and media area']);

    // Pencarian mengabaikan tab dan menyembunyikannya, seperti di Moodle.
    const search = dialog().querySelector('input[type="search"]');
    await act(async () => fill(search, 'qui'));
    expect(tileNames()).toEqual(['Quiz']);
    expect(dialog().querySelector('[role="tablist"]')).toBeNull();
    await act(async () => fill(search, 'zzz'));
    expect(dialog().textContent).toContain('No results for "zzz".');
  });

  it('bintang menentukan isi tab Starred dan tersimpan untuk pengguna', async () => {
    await openChooser();
    await click(dialog().querySelector('[aria-label="Unstar Quiz"]'));
    expect(tileNames()).toEqual(['Assignment', 'Text and media area']);
    await tab('All');
    expect(tileNames()).toEqual(['Assignment', 'Quiz', 'Text and media area']);
    expect(dialog().querySelector('[aria-label="Star Quiz"]').getAttribute('aria-pressed')).toBe('false');

    // Tutup lalu buka lagi: pilihan bintang bertahan.
    await click(dialog().querySelector('[aria-label="Tutup"]'));
    await waitFor(() => !q('dialog'), 'dialog tertutup');
    await openAdd();
    expect(tileNames()).toEqual(['Assignment', 'Text and media area']);
  });

  it('tombol info menampilkan deskripsi dan Add membuka halaman New Assignment', async () => {
    await openChooser();
    await click(dialog().querySelector('[aria-label="Assignment info"]'));
    expect(dialog().textContent).toContain('set tasks, collect students');
    await click(button('← Back'));
    expect(tileNames()).toHaveLength(3);
    await click(dialog().querySelector('[aria-label="Assignment info"]'));
    await click(button('Add'));
    await waitFor(() => pageHeading() === 'New Assignment', 'halaman New Assignment');
    expect(container.textContent).not.toContain('Add an activity or resource');
  });

  // ---- Halaman "New <aktivitas>" seperti course/modedit.php.
  const pageHeading = () => [...container.querySelectorAll('h2')].map((h) => h.textContent).find((t) => t.startsWith('New ')) ?? null;
  const field = (text) => {
    const label = [...container.querySelectorAll('form label')].find((l) => l.textContent.replace(/Required field|!/g, '').trim() === text);
    return label.htmlFor ? document.getElementById(label.htmlFor) : label.querySelector('input');
  };
  const sectionToggle = (title) => [...container.querySelectorAll('form fieldset button[aria-expanded]')].find((b) => b.textContent === title);
  function dateGroup(label) {
    const span = [...container.querySelectorAll('form span[id]')].find((s) => s.textContent === label);
    return container.querySelector(`[role="group"][aria-labelledby="${span.id}"]`);
  }
  async function setSelect(select, value) {
    await act(async () => {
      select.value = String(value);
      select.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }
  const dateSelect = (label, part) => dateGroup(label).querySelector(`select[aria-label="${part}"]`);
  const enable = (label) => dateGroup(label).querySelector('input[type="checkbox"]');
  async function typeEditor(index, html) {
    await act(async () => {
      const editor = container.querySelectorAll('form [role="textbox"][contenteditable]')[index];
      editor.innerHTML = html;
      editor.dispatchEvent(new Event('input', { bubbles: true }));
    });
  }
  async function openModEdit(name, sectionNumber = 1) {
    await openChooser(sectionNumber);
    await chooseType(name);
    await waitFor(() => pageHeading() === `New ${name}`, `halaman New ${name}`);
  }

  it('membuat tugas lewat halaman New Assignment seperti Moodle', async () => {
    await openModEdit('Assignment');
    expect(q('[aria-label="Breadcrumb aktivitas"]').textContent).toBe('Minggu 1: Pengantar Pemrograman Web / New Assignment');
    // Bagian dan bawaan mengikuti mod_form.php: General, Availability, Submission types terbuka; Grade tertutup.
    expect(['General', 'Availability', 'Submission types', 'Grade'].map((t) => sectionToggle(t).getAttribute('aria-expanded'))).toEqual(['true', 'true', 'true', 'false']);
    expect(enable('Allow submissions from').checked).toBe(true);
    expect(enable('Due date').checked).toBe(true);
    expect(enable('Cut-off date').checked).toBe(false);
    expect(dateSelect('Cut-off date', 'Day').disabled).toBe(true);
    expect(field('Online text').checked).toBe(false);
    expect(field('File submissions').checked).toBe(true);
    expect(button('Save and display')).toBeTruthy();

    await click(button('Save and return to course'));
    expect(container.textContent).toContain('You must supply a value here.');
    expect(field('Assignment name').getAttribute('aria-invalid')).toBe('true');

    await act(async () => fill(field('Assignment name'), 'Tugas Pengantar'));
    await typeEditor(0, '<p>Buat ringkasan <strong>HTTP</strong>.</p>');
    const year = Number(dateSelect('Due date', 'Year').value);
    await setSelect(dateSelect('Due date', 'Year'), year - 1);
    await click(button('Save and return to course'));
    expect(container.textContent).toContain('Due date cannot be earlier than the allow submissions from date.');
    expect(container.textContent).not.toContain('You must supply a value here.');
    await setSelect(dateSelect('Due date', 'Year'), year);

    await click(enable('Cut-off date'));
    expect(dateSelect('Cut-off date', 'Day').disabled).toBe(false);
    await setSelect(dateSelect('Cut-off date', 'Year'), year - 1);
    await click(button('Save and return to course'));
    expect(container.textContent).toContain('Cut-off date cannot be earlier than the due date.');
    await setSelect(dateSelect('Cut-off date', 'Year'), year + 1);

    // Jenis pengumpulan: Word limit muncul setelah Online text dicentang, aktif setelah Enable.
    expect(container.textContent).not.toContain('Word limit');
    await click(field('Online text'));
    expect(field('Word limit').disabled).toBe(true);
    await click(field('Word limit').parentElement.querySelector('input[type="checkbox"]'));
    await act(async () => fill(field('Word limit'), '250'));
    await setSelect(field('Maximum number of uploaded files'), 3);

    // Error di bagian yang tertutup membuka bagian itu.
    await click(button('Expand all'));
    expect(sectionToggle('Grade').getAttribute('aria-expanded')).toBe('true');
    expect(button('Collapse all')).toBeTruthy();
    await act(async () => fill(field('Maximum grade'), '150'));
    await click(sectionToggle('Grade'));
    await click(button('Save and display'));
    expect(container.textContent).toContain('Invalid grade value. This must be an integer between 1 and 100');
    await waitFor(() => sectionToggle('Grade').getAttribute('aria-expanded') === 'true', 'bagian Grade terbuka');
    await act(async () => fill(field('Maximum grade'), '80'));

    await click(button('Save and display'));
    await waitFor(() => [...container.querySelectorAll('h2')].some((h) => h.textContent === 'Tugas Pengantar'), 'halaman tugas baru');
    expect(container.textContent).toContain('Tugas ditambahkan.');
    const created = (await getAssignments([2])).find((a) => a.name === 'Tugas Pengantar');
    expect(created).toMatchObject({ grade: 80, intro: '<p>Buat ringkasan <strong>HTTP</strong>.</p>' });
    expect(created.cutoffdate).toBeGreaterThan(created.duedate);
    expect(submissionTypes(created)).toEqual({ onlineText: true, wordLimit: 250, files: true, maxFiles: 3, maxBytes: 1024 * 1024 });
  });

  it('membuat quiz lewat halaman New Quiz; Save and return kembali ke kursus', async () => {
    await openModEdit('Quiz');
    expect(['General', 'Timing'].map((t) => sectionToggle(t).getAttribute('aria-expanded'))).toEqual(['true', 'false']);
    await click(button('Save and return to course'));
    expect(container.textContent).toContain('You must supply a value here.');
    await act(async () => fill(field('Name'), 'Kuis Pengantar HTTP'));
    await click(sectionToggle('Timing'));
    await click(enable('Open the quiz'));
    await click(enable('Close the quiz'));
    const year = Number(dateSelect('Open the quiz', 'Year').value);
    await setSelect(dateSelect('Close the quiz', 'Year'), year - 1);
    await click(button('Save and return to course'));
    expect(container.textContent).toContain('The close date must be after the open date.');
    await setSelect(dateSelect('Close the quiz', 'Year'), year);

    await click(button('Save and return to course'));
    await waitFor(() => q('#section-1 [aria-label="Aksi untuk Kuis Pengantar HTTP"]'), 'quiz baru di Minggu 1');
    expect(container.textContent).toContain('Kuis ditambahkan.');
    const row = q('#section-1 [aria-label="Aksi untuk Kuis Pengantar HTTP"]').closest('li');
    expect(row.textContent).toContain('Dibuka:');
    expect(row.textContent).toContain('Ditutup:');
  });

  it('membuat Text and media area dari editor; HTML berbahaya dibuang', async () => {
    await openModEdit('Text and media area', 0);
    expect(button('Save and display')).toBeUndefined();
    await click(button('Save and return to course'));
    expect(container.textContent).toContain('You must supply a value here.');
    await act(async () => fill(field('Title in course index'), 'Sambutan'));
    await typeEditor(0, '<p>Selamat datang <b>di kelas</b>.</p><img src="x" onerror="window.__xss = 1">');
    await click(button('Save and return to course'));
    await waitFor(() => container.textContent.includes('Teks dan media ditambahkan.'), 'toast');
    const general = q('#section-0');
    expect(general.textContent).toContain('Selamat datang di kelas.');
    expect(general.querySelector('b').textContent).toBe('di kelas');
    expect(general.querySelector('img[onerror]')).toBeNull();
    expect(window.__xss).toBeUndefined();
    expect(findCm(await getCourseContents(2), 'Sambutan')).toMatchObject({ modname: 'label' });
  });

  it('Cancel kembali ke kursus tanpa menyimpan apa pun', async () => {
    await openModEdit('Assignment');
    await act(async () => fill(field('Assignment name'), 'Draf'));
    await click([...container.querySelectorAll('form button')].find((b) => b.textContent === 'Cancel' && !b.closest('dialog')));
    await waitFor(() => !pageHeading() && q('#section-1'), 'kembali ke kursus');
    expect(container.textContent).not.toContain('Tugas ditambahkan.');
    expect(findCm(await getCourseContents(2), 'Draf')).toBeUndefined();
  });

  it('halaman New activity tertutup bagi pengguna yang tidak boleh mengubah kursus', async () => {
    await render('/course/2/modedit?add=assign&section=1', 'mahasiswa');
    await waitForText('Anda tidak dapat menambah aktivitas di kursus ini.');
    expect(pageHeading()).toBeNull();
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
    expect(q('[aria-label="Aksi untuk section General"]')).not.toBeNull();
    // Tampilan disegarkan mengikuti Moodle: aktivitas yang sudah dihapus tidak lagi tampil.
    await waitFor(() => !q('[aria-label="Aksi untuk Kuis 3"]'), 'daftar disegarkan');
  });
});
