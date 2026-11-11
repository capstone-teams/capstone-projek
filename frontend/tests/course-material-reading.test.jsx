import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ActivityRow from '../src/components/moodle/course/ActivityRow';
import ActivityView from '../src/components/moodle/course/ActivityView';
import { publishSummary } from '../src/services/publishService';
import { withHeadingAnchors } from '../src/utils/htmlText';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockCourse = vi.hoisted(() => ({ value: null }));
vi.mock('../src/hooks/useMoodleCourse', () => ({
  useMoodleCourse: () => mockCourse.value,
  useCourseBreadcrumb: () => {},
}));

const longMaterial = `<h2>Konsep Normalisasi</h2><p>${'Normalisasi mengurangi redundansi data. '.repeat(30)}</p>`
  + '<h2>Bentuk Normal Kedua</h2><p>2NF menghilangkan dependensi parsial.</p>'
  + '<figure><img src="https://kroki.io/mermaid/svg/abc" alt="Alur normalisasi"><figcaption>Alur normalisasi</figcaption></figure>';
const page = { id: 512, name: 'Minggu 3: Normalisasi', modname: 'page', content: longMaterial, visible: 1, uservisible: true };

describe('membaca materi mingguan', () => {
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
  });

  const render = async (node, path = '/course/48') => {
    root = createRoot(container);
    await act(async () => root.render(<MemoryRouter initialEntries={[path]}>{node}</MemoryRouter>));
  };

  it('kartu minggu menampilkan pratinjau materi panjang dan tautan "Baca selengkapnya" ke halaman materi', async () => {
    await render(<ul><ActivityRow courseId={48} mod={page} isTeacher={false} editMode={false} sections={[]} /></ul>);
    const preview = container.querySelector('[data-testid="page-preview"]');
    expect(preview.className).toContain('max-h-56');
    expect(preview.textContent).toContain('Normalisasi mengurangi redundansi data.');
    const link = [...container.querySelectorAll('a')].find((a) => a.textContent.includes('Baca selengkapnya'));
    expect(link.getAttribute('href')).toBe('/course/48/mod/512');
    expect(container.textContent).toMatch(/± \d+ menit baca/);
  });

  it('materi pendek tampil utuh tanpa dipotong', async () => {
    await render(<ul><ActivityRow courseId={48} mod={{ ...page, content: '<p>Materi singkat.</p>' }} isTeacher={false} editMode={false} sections={[]} /></ul>);
    expect(container.querySelector('[data-testid="page-preview"]').className).not.toContain('max-h-56');
    expect(container.textContent).toContain('Buka halaman materi →');
  });

  it('halaman materi tampil sebagai artikel dengan daftar isi dan ilustrasi', async () => {
    mockCourse.value = { course: { id: 48 }, sections: [{ id: 10, section: 3, name: 'Pertemuan 3', modules: [page] }], reload: vi.fn() };
    await render(
      <Routes><Route path="/course/:courseId/mod/:cmid" element={<ActivityView renderAssign={() => null} />} /></Routes>,
      '/course/48/mod/512',
    );
    const article = container.querySelector('article');
    expect(article.querySelector('.prose-article')).not.toBeNull();
    expect(article.textContent).toContain('Pertemuan 3');
    const toc = container.querySelector('nav[aria-label="Daftar isi"]');
    expect([...toc.querySelectorAll('a')].map((a) => a.textContent)).toEqual(['Konsep Normalisasi', 'Bentuk Normal Kedua']);
    expect(article.querySelector('img').getAttribute('src')).toBe('https://kroki.io/mermaid/svg/abc');
    expect(article.querySelector('h2').id).toMatch(/^bagian-1/);
  });
});

describe('utilitas', () => {
  it('heading h2/h3 diberi id untuk daftar isi', () => {
    const { headings, html } = withHeadingAnchors('<h2>Pengantar</h2><p>x</p><h3>Detail</h3>');
    expect(headings.map((h) => [h.text, h.level])).toEqual([['Pengantar', 2], ['Detail', 3]]);
    expect(html).toContain(`id="${headings[0].id}"`);
  });

  it('ringkasan publikasi: yang disetujui sekarang, sudah disetujui, dan dilewati', () => {
    const summary = publishSummary([
      { id: 'a', status: 'DRAFT', validation: { status: 'PASSED' } },
      { id: 'b', status: 'APPROVED', validation: { status: 'PASSED' } },
      { id: 'c', status: 'DRAFT', validation: { status: 'FAILED' } },
    ]);
    expect(summary.toApprove.map((item) => item.id)).toEqual(['a']);
    expect(summary.approved.map((item) => item.id)).toEqual(['b']);
    expect(summary.skipped.map((item) => item.id)).toEqual(['c']);
    expect(summary.publishable).toBe(2);
  });
});
