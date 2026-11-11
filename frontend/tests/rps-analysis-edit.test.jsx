import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import RpsAnalysisEditor from '../src/components/ai/course/RpsAnalysisEditor';

// Design-api §6.7: dosen mengoreksi hasil analisis RPS lewat web. Editor mengirim balik
// objek hasil parse — validasi skema tetap milik server.
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const DATA = {
  schema_version: '2.0',
  course: { name: 'Arsitektur Komputer', code: 'IF201407', credits: 3 },
  weeks: [{ week: 1, topics: ['Pengenalan Arsitektur Komputer'] }],
};

function setTextarea(textarea, value) {
  const setter = Object.getOwnPropertyDescriptor(
    window.HTMLTextAreaElement.prototype,
    'value',
  ).set;
  setter.call(textarea, value);
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
}

describe('RpsAnalysisEditor', () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  async function render(props = {}) {
    const onSave = props.onSave ?? vi.fn().mockResolvedValue(undefined);
    await act(async () =>
      root.render(
        <RpsAnalysisEditor
          data={DATA}
          onSave={onSave}
          onCancel={props.onCancel ?? (() => {})}
          saving={props.saving ?? false}
          error={props.error ?? null}
        />,
      ),
    );
    return onSave;
  }

  it('menampilkan data tersimpan dan mengirim hasil edit saat disimpan', async () => {
    const onSave = await render();
    const textarea = container.querySelector('textarea');
    expect(JSON.parse(textarea.value).course.name).toBe('Arsitektur Komputer');

    const edited = { ...DATA, course: { ...DATA.course, credits: 4 } };
    await act(async () => setTextarea(textarea, JSON.stringify(edited, null, 2)));
    await act(async () => container.querySelector('button[type="submit"]').click());

    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onSave.mock.calls[0][0]).toEqual(edited);
  });

  it('menolak JSON rusak tanpa memanggil server', async () => {
    const onSave = await render();
    const textarea = container.querySelector('textarea');

    await act(async () => setTextarea(textarea, '{ "course": '));
    await act(async () => container.querySelector('button[type="submit"]').click());

    expect(onSave).not.toHaveBeenCalled();
    expect(container.textContent).toContain('JSON tidak valid');
    expect(textarea.getAttribute('aria-invalid')).toBe('true');
  });
});
