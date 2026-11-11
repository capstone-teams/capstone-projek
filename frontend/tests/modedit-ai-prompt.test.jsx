import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { AssignModForm, LabelModForm, QuizModForm } from '../src/components/moodle/modedit/ModForms';
import { MAX_OPTIONS, MIN_OPTIONS, newQuestion, toQuestionFields, validateQuestions } from '../src/utils/quizQuestions';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe('soal pilihan ganda (utils/quizQuestions)', () => {
  it('memeriksa pertanyaan, jumlah pilihan, dan kunci jawaban', () => {
    const empty = newQuestion();
    expect(empty.options).toHaveLength(4);
    expect(validateQuestions([empty])).toEqual({ 0: 'Pertanyaan wajib diisi.' });
    expect(validateQuestions([{ ...empty, text: 'Apa itu SQL?', options: ['Bahasa query', '', '', ''] }])).toEqual({ 0: `Isi minimal ${MIN_OPTIONS} pilihan jawaban.` });
    expect(validateQuestions([{ ...empty, text: 'Apa itu SQL?', options: ['A', 'B', '', ''], correct: 2 }])).toEqual({ 0: 'Pilih kunci jawaban dari pilihan yang terisi.' });
    expect(validateQuestions([{ ...empty, text: 'Apa itu SQL?', options: ['A', 'B', '', ''], correct: 1 }])).toEqual({});
  });

  it('membuang pilihan kosong dan menyesuaikan indeks kunci jawaban', () => {
    expect(toQuestionFields([{ key: 'x', text: ' Apa itu JOIN? ', options: ['', 'Gabung tabel', '  ', 'Hapus tabel'], correct: 3 }]))
      .toEqual([{ text: 'Apa itu JOIN?', options: ['Gabung tabel', 'Hapus tabel'], correct_index: 1 }]);
    expect(MAX_OPTIONS).toBe(6);
  });
});

describe('Form aktivitas baru: generate otomatis dan quiz', () => {
  let container;
  let root;
  let onSubmit;
  const mount = async (Form, props = {}) => {
    root = createRoot(container);
    await act(async () => root.render(<Form canCreate pending={false} error={null} onSubmit={onSubmit} onCancel={() => {}} {...props} />));
  };
  const setValue = async (element, value) => {
    const setter = Object.getOwnPropertyDescriptor(element.constructor.prototype, 'value').set;
    await act(async () => {
      setter.call(element, value);
      element.dispatchEvent(new Event(element.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }));
    });
  };
  const click = (element) => act(async () => element.click());
  const button = (text) => [...container.querySelectorAll('button')].find((b) => b.textContent.trim() === text);
  const prompt = () => container.querySelector('textarea[id$="-ai"]');
  const save = () => act(async () => container.querySelector('form').requestSubmit());
  const toggle = (title) => [...container.querySelectorAll('button[aria-expanded]')].find((b) => b.textContent.trim() === title);

  beforeEach(() => {
    onSubmit = vi.fn();
    container = document.createElement('div');
    document.body.appendChild(container);
  });
  afterEach(() => {
    act(() => root?.unmount());
    container.remove();
  });

  it.each([
    ['Assignment', AssignModForm, /tugas studi kasus/i],
    ['Text and media area', LabelModForm, /ringkasan materi/i],
  ])('%s: bagian Generate otomatis (AI) terbuka, prompt tambahan, dan tombol generate menunggu layanan', async (_name, Form, example) => {
    await mount(Form);
    expect(toggle('Generate otomatis (AI)').getAttribute('aria-expanded')).toBe('true');
    expect(container.querySelector(`label[for="${prompt().id}"]`).textContent).toBe('Prompt tambahan');
    expect(prompt().placeholder).toMatch(example);
    expect(prompt().maxLength).toBe(2000);
    expect(button('Generate dengan AI').disabled).toBe(true);
    expect(container.textContent).toContain('Generate isi aktivitas dengan AI belum tersedia.');
  });

  it('tombol generate aktif bila halaman memberi onGenerate', async () => {
    const onGenerate = vi.fn();
    await mount(AssignModForm, { onGenerate });
    expect(button('Generate dengan AI').disabled).toBe(false);
    await click(button('Generate dengan AI'));
    expect(onGenerate).toHaveBeenCalledTimes(1);
    expect(container.textContent).not.toContain('belum tersedia');
  });

  it('prompt tambahan dikirim terpisah dari isian aktivitas (Text and media area)', async () => {
    await mount(LabelModForm);
    const editor = container.querySelector('[role="textbox"]');
    await act(async () => {
      editor.innerHTML = '<p>Materi minggu 1</p>';
      editor.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await setValue(prompt(), '  Ringkas materi ini.  ');
    await save();
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const [fields, ai] = onSubmit.mock.calls[0];
    expect(fields).toMatchObject({ text: '<p>Materi minggu 1</p>', format: 1 });
    expect(JSON.stringify(fields)).not.toContain('Ringkas');
    expect(ai).toEqual({ aiPrompt: 'Ringkas materi ini.' });
  });

  it('draf AI mengisi nama dan isi Text and media area tanpa menimpa nama yang sudah diisi dosen', async () => {
    const onGenerate = vi.fn().mockResolvedValue({ name: 'Pengantar Minggu 3', text: '<p>Ringkasan normalisasi.</p>', references_used: ['File: slide.pdf'] });
    await mount(LabelModForm, { onGenerate });
    await setValue(container.querySelector('input[id$="-name"]'), 'Judul saya');
    await click(button('Generate dengan AI'));
    expect(container.querySelector('input[id$="-name"]').value).toBe('Judul saya');
    expect(container.querySelector('[role="textbox"]').innerHTML).toContain('Ringkasan normalisasi.');
    expect(container.textContent).toContain('Draf dibuat dari: File: slide.pdf.');
    await save();
    expect(onSubmit.mock.calls[0][0]).toMatchObject({ name: 'Judul saya', text: '<p>Ringkasan normalisasi.</p>' });
  });

  it('galat generate ditampilkan tanpa mengubah isian', async () => {
    const onGenerate = vi.fn().mockRejectedValue(new Error('Belum ada referensi untuk minggu ini.'));
    await mount(AssignModForm, { onGenerate });
    await click(button('Generate dengan AI'));
    expect(container.querySelector('[role="alert"]').textContent).toBe('Belum ada referensi untuk minggu ini.');
    expect(container.querySelector('input[id$="-name"]').value).toBe('');
  });

  it('hanya ada satu tombol simpan', async () => {
    await mount(AssignModForm);
    expect(button('Save and return to course')).toBeTruthy();
    expect(button('Save and display')).toBeUndefined();
  });

  describe('Quiz', () => {
    const questionBox = (n) => container.querySelector(`[data-question="${n}"]`);
    const optionInput = (n, letter) => container.querySelector(`input[aria-label="Pilihan ${letter} soal ${n}"]`);

    it('bagian Soal terbuka dengan mode Buat manual sebagai bawaan', async () => {
      await mount(QuizModForm);
      expect(toggle('Soal').getAttribute('aria-expanded')).toBe('true');
      expect(container.querySelector('input[type="radio"]:checked').parentElement.textContent).toContain('Buat manual');
      expect(container.textContent).toContain('Belum ada soal.');
    });

    it('membuat soal pilihan ganda secara manual dan menyimpannya bersama quiz', async () => {
      await mount(QuizModForm);
      await setValue(container.querySelector('input[id$="-name"]'), 'Kuis SQL');
      await click(button('+ Tambah soal'));
      await setValue(questionBox(1).querySelector('textarea'), 'Perintah untuk membaca data?');
      await setValue(optionInput(1, 'A'), 'INSERT');
      await setValue(optionInput(1, 'B'), 'SELECT');
      await setValue(optionInput(1, 'C'), 'DELETE');
      await click(container.querySelector('input[aria-label="Jadikan pilihan B kunci jawaban"]'));
      await save();
      expect(onSubmit).toHaveBeenCalledTimes(1);
      const [fields, ai] = onSubmit.mock.calls[0];
      expect(fields).toMatchObject({ name: 'Kuis SQL', questions: [{ text: 'Perintah untuk membaca data?', options: ['INSERT', 'SELECT', 'DELETE'], correct_index: 1 }] });
      expect(ai).toEqual({ aiPrompt: '', aiQuestionCount: 10, aiDifficulty: 'sedang' });
    });

    it('soal yang belum lengkap menahan penyimpanan dan menandai soalnya', async () => {
      await mount(QuizModForm);
      await setValue(container.querySelector('input[id$="-name"]'), 'Kuis SQL');
      await click(button('+ Tambah soal'));
      await setValue(questionBox(1).querySelector('textarea'), 'Apa itu SQL?');
      await setValue(optionInput(1, 'A'), 'Bahasa query');
      await setValue(optionInput(1, 'B'), 'Bahasa markup');
      await save();
      expect(onSubmit).not.toHaveBeenCalled();
      expect(questionBox(1).textContent).toContain('Pilih kunci jawaban dari pilihan yang terisi.');
      expect(questionBox(1).querySelector('textarea').getAttribute('aria-invalid')).toBe('true');
      // Mengubah soal menghapus tanda galat.
      await click(container.querySelector('input[aria-label="Jadikan pilihan A kunci jawaban"]'));
      expect(questionBox(1).textContent).not.toContain('Pilih kunci jawaban');
      await save();
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });

    it('menambah dan menghapus pilihan dalam batas 2 sampai 6, serta menghapus soal', async () => {
      await mount(QuizModForm);
      await click(button('+ Tambah soal'));
      await click(button('+ Pilihan'));
      await click(button('+ Pilihan'));
      expect(questionBox(1).querySelectorAll('input[aria-label^="Pilihan"]')).toHaveLength(6);
      expect(button('+ Pilihan').disabled).toBe(true);
      for (let i = 0; i < 4; i += 1) await click(container.querySelector('button[aria-label="Hapus pilihan A soal 1"]'));
      expect(questionBox(1).querySelectorAll('input[aria-label^="Pilihan"]')).toHaveLength(2);
      expect(container.querySelector('button[aria-label="Hapus pilihan A soal 1"]').disabled).toBe(true);
      await click(button('Hapus soal'));
      expect(questionBox(1)).toBeNull();
    });

    it('menghapus pilihan menggeser kunci jawaban yang berada setelahnya', async () => {
      await mount(QuizModForm);
      await setValue(container.querySelector('input[id$="-name"]'), 'Kuis');
      await click(button('+ Tambah soal'));
      await setValue(questionBox(1).querySelector('textarea'), 'Pilih D');
      for (const [letter, text] of [['A', 'a'], ['B', 'b'], ['C', 'c'], ['D', 'd']]) await setValue(optionInput(1, letter), text);
      await click(container.querySelector('input[aria-label="Jadikan pilihan D kunci jawaban"]'));
      await click(container.querySelector('button[aria-label="Hapus pilihan A soal 1"]'));
      await save();
      expect(onSubmit.mock.calls[0][0].questions).toEqual([{ text: 'Pilih D', options: ['b', 'c', 'd'], correct_index: 2 }]);
    });

    it('mode Generate otomatis: prompt, jumlah soal, tingkat kesulitan, dan tombol yang menunggu layanan', async () => {
      await mount(QuizModForm);
      await setValue(container.querySelector('input[id$="-name"]'), 'Kuis AI');
      await click([...container.querySelectorAll('input[type="radio"]')].find((r) => r.parentElement.textContent.includes('Generate otomatis')));
      expect(container.querySelector('input[type="number"][id$="-count"]').value).toBe('10');
      await setValue(container.querySelector('textarea[id$="-quiz-ai"]'), 'Soal tentang normalisasi.');
      await setValue(container.querySelector('input[id$="-count"]'), '15');
      await setValue(container.querySelector('select[id$="-difficulty"]'), 'sulit');
      expect(button('Generate soal dengan AI').disabled).toBe(true);
      expect(container.textContent).toContain('Generate soal quiz dengan AI belum tersedia.');
      // Quiz dibuat beserta soalnya: tanpa soal (belum di-generate) tidak ada yang tersimpan.
      await save();
      expect(onSubmit).not.toHaveBeenCalled();
      expect(container.textContent).toContain('Quiz wajib memiliki minimal satu soal.');
    });

    it('soal hasil generate AI masuk ke editor manual, lengkap dengan kunci dan pembahasan', async () => {
      const onGenerate = vi.fn().mockResolvedValue({
        name: 'Kuis Normalisasi',
        intro: '<p>Kerjakan dengan teliti.</p>',
        questions: [{
          question_text: 'Bentuk normal yang menghilangkan dependensi parsial?',
          options: [{ key: 'A', text: '1NF' }, { key: 'B', text: '2NF' }, { key: 'C', text: '3NF' }, { key: 'D', text: 'BCNF' }],
          correct_option_key: 'B',
          explanation: '2NF menghilangkan dependensi parsial.',
        }],
        references_used: ['Materi minggu ini', 'RPS kursus'],
      });
      await mount(QuizModForm, { onGenerate });
      await click([...container.querySelectorAll('input[type="radio"]')].find((r) => r.parentElement.textContent.includes('Generate otomatis')));
      await setValue(container.querySelector('input[id$="-count"]'), '5');
      await click(button('Generate soal dengan AI'));
      expect(onGenerate).toHaveBeenCalledWith(expect.objectContaining({ aiQuestionCount: 5, aiDifficulty: 'sedang', useWeek: true, useRps: true, file: null }));
      // Pindah ke mode manual dengan soal terisi; nama kosong diisi dari draf.
      expect(container.querySelector('input[id$="-name"]').value).toBe('Kuis Normalisasi');
      expect(questionBox(1).querySelector('textarea').value).toBe('Bentuk normal yang menghilangkan dependensi parsial?');
      expect(container.textContent).toContain('Draf dibuat dari: Materi minggu ini, RPS kursus.');
      await save();
      expect(onSubmit.mock.calls[0][0].questions).toEqual([{
        text: 'Bentuk normal yang menghilangkan dependensi parsial?',
        options: ['1NF', '2NF', '3NF', 'BCNF'],
        correct_index: 1,
        explanation: '2NF menghilangkan dependensi parsial.',
      }]);
    });

    it('validasi Moodle tetap berlaku: tanpa nama tidak ada yang terkirim', async () => {
      await mount(QuizModForm);
      await save();
      expect(onSubmit).not.toHaveBeenCalled();
      expect(container.textContent).toContain('You must supply a value here.');
    });
  });
});
