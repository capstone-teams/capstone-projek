import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ActivityView from '../src/components/moodle/course/ActivityView';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// Isi kursus yang dimuat layout sebelum eksekusi Moodle dari tab Generator AI: activity baru belum ada.
const mockCourse = vi.hoisted(() => ({ value: null }));

vi.mock('../src/hooks/useMoodleCourse', () => ({
  useMoodleCourse: () => mockCourse.value,
  useCourseBreadcrumb: () => {},
}));

const staleSections = [{ id: 10, section: 1, name: 'Minggu 1', modules: [] }];
const freshSections = [{
  id: 10,
  section: 1,
  name: 'Minggu 1',
  modules: [{ id: 512, name: 'Minggu 1: Konsep Basis Data', modname: 'page', content: '<p>Isi materi hasil generate.</p>', visible: 1, uservisible: true }],
}];

describe('Halaman activity dengan isi kursus yang belum diperbarui', () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(async () => {
    await act(async () => root?.unmount());
    root = null;
    container.remove();
    vi.restoreAllMocks();
  });

  async function render() {
    root = createRoot(container);
    await act(async () => {
      root.render(
        <MemoryRouter initialEntries={['/course/48/mod/512']}>
          <Routes>
            <Route path="/course/:courseId/mod/:cmid" element={<ActivityView renderAssign={() => null} />} />
          </Routes>
        </MemoryRouter>,
      );
    });
  }

  it('memuat ulang isi kursus sekali lalu menampilkan activity baru, bukan "Aktivitas tidak ditemukan"', async () => {
    const reload = vi.fn(async () => {
      mockCourse.value = { ...mockCourse.value, sections: freshSections };
    });
    mockCourse.value = { course: { id: 48 }, sections: staleSections, reload };

    await render();
    expect(reload).toHaveBeenCalledTimes(1);
    expect(reload).toHaveBeenCalledWith({ silent: true });
    // Layout memberi isi kursus baru lewat context setelah reload.
    await act(async () => root.render(
      <MemoryRouter initialEntries={['/course/48/mod/512']}>
        <Routes>
          <Route path="/course/:courseId/mod/:cmid" element={<ActivityView renderAssign={() => null} />} />
        </Routes>
      </MemoryRouter>,
    ));
    expect(container.textContent).toContain('Isi materi hasil generate.');
    expect(container.textContent).not.toContain('Aktivitas tidak ditemukan');
  });

  it('tetap menampilkan "Aktivitas tidak ditemukan" bila activity memang tidak ada setelah dimuat ulang', async () => {
    const reload = vi.fn(async () => {});
    mockCourse.value = { course: { id: 48 }, sections: staleSections, reload };

    await render();
    expect(reload).toHaveBeenCalledTimes(1);
    expect(container.textContent).toContain('Aktivitas tidak ditemukan');
  });
});
