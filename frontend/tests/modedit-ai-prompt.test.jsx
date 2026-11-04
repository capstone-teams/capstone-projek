import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { AssignModForm, LabelModForm, QuizModForm } from '../src/components/moodle/modedit/ModForms';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe('Prompt AI pada formulir aktivitas baru', () => {
  let container;
  let root;
  let onSubmit;
  const mount = async (Form) => {
    root = createRoot(container);
    await act(async () => root.render(<Form canCreate pending={false} error={null} onSubmit={onSubmit} onCancel={() => {}} />));
  };
  const setValue = async (element, value) => {
    const setter = Object.getOwnPropertyDescriptor(element.constructor.prototype, 'value').set;
    await act(async () => {
      setter.call(element, value);
      element.dispatchEvent(new Event('input', { bubbles: true }));
    });
  };
  const prompt = () => container.querySelector('textarea[id$="-ai"]');
  const save = () => act(async () => container.querySelector('form').requestSubmit());

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
    ['Quiz', QuizModForm, /soal pilihan ganda/i],
    ['Text and media area', LabelModForm, /ringkasan materi/i],
  ])('%s punya bagian Generator AI yang terbuka dengan contoh isian', async (_name, Form, example) => {
    await mount(Form);
    const toggle = [...container.querySelectorAll('button[aria-expanded]')].find((button) => button.textContent.trim() === 'Generator AI');
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(prompt()).not.toBeNull();
    expect(container.querySelector(`label[for="${prompt().id}"]`).textContent).toBe('Prompt AI');
    expect(prompt().placeholder).toMatch(example);
    expect(prompt().getAttribute('aria-describedby')).toBe(`${prompt().id.replace(/-ai$/, '')}-ai-hint`);
    expect(prompt().maxLength).toBe(2000);
  });

  it('prompt diteruskan sebagai argumen ketiga dan tidak ikut dalam isian aktivitas (Quiz)', async () => {
    await mount(QuizModForm);
    await setValue(container.querySelector('input[id$="-name"]'), 'Kuis SQL');
    await setValue(prompt(), '  Buat 5 soal tentang join.  ');
    expect(container.textContent).toContain('29/2000');
    await save();
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const [fields, display, ai] = onSubmit.mock.calls[0];
    expect(fields).toMatchObject({ name: 'Kuis SQL' });
    expect(Object.keys(fields).join()).not.toMatch(/prompt/i);
    expect(JSON.stringify(fields)).not.toContain('join');
    expect(display).toBe(false);
    expect(ai).toEqual({ aiPrompt: 'Buat 5 soal tentang join.' });
  });

  it('prompt kosong tetap opsional dan terkirim sebagai teks kosong (Assignment)', async () => {
    await mount(AssignModForm);
    await setValue(container.querySelector('input[id$="-name"]'), 'Tugas 1');
    await save();
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][2]).toEqual({ aiPrompt: '' });
    expect(Object.keys(onSubmit.mock.calls[0][0]).join()).not.toMatch(/prompt/i);
  });

  it('Text and media area mengirim prompt bersama teks dari editor', async () => {
    await mount(LabelModForm);
    const editor = container.querySelector('[role="textbox"]');
    await act(async () => {
      editor.innerHTML = '<p>Materi minggu 1</p>';
      editor.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await setValue(prompt(), 'Ringkas materi ini.');
    await save();
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0]).toMatchObject({ text: '<p>Materi minggu 1</p>', format: 1 });
    expect(onSubmit.mock.calls[0][2]).toEqual({ aiPrompt: 'Ringkas materi ini.' });
  });

  it('validasi form Moodle tetap berlaku: tanpa nama tidak ada yang terkirim walau prompt terisi', async () => {
    await mount(QuizModForm);
    await setValue(prompt(), 'Buat soal.');
    await save();
    expect(onSubmit).not.toHaveBeenCalled();
    expect(container.textContent).toContain('You must supply a value here.');
  });
});
