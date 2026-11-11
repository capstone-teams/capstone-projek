import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useCourseBreadcrumb, useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useApi } from '../../../hooks/useApi';
import { getAssignments, getPages } from '../../../services/moodle/moodleApi';
import { withToken } from '../../../services/moodle/moodleClient';
import { Card, EmptyState, ErrorAlert, Spinner } from '../../ui';
import ActivityIcon from '../ActivityIcon';
import MoodleHtml from '../MoodleHtml';
import { AssignIntro } from '../AssignSubmission';
import { formatUnixDateTime } from '../../../utils/format';
import { htmlToText, readingMinutes, withHeadingAnchors } from '../../../utils/htmlText';

function PageContent({ course, mod, section }) {
  const { data, error, loading } = useApi(() => getPages([course.id]), [course.id]);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;
  const page = data.find((p) => String(p.coursemodule) === String(mod.id));
  // Lewat Backend Gateway isi Page sudah ikut di modul (GET /integrations/moodle/courses/{id}/contents).
  const html = page?.content || mod.content || mod.description;
  if (!html) return <EmptyState title="Isi halaman belum tersedia.">Moodle belum mengirim isi halaman ini. Coba muat ulang beberapa saat lagi.</EmptyState>;
  return <PageArticle course={course} section={section} html={html} />;
}

/**
 * Isi Page sebagai artikel: lebar baca nyaman, perkiraan waktu baca, daftar isi dari heading (h2/h3), serta gambar
 * dan diagram selebar kolom. Daftar isi tampil di samping pada layar lebar dan di atas pada layar sempit.
 */
function PageArticle({ course, section, html }) {
  const { html: anchored, headings } = useMemo(() => withHeadingAnchors(html), [html]);
  const minutes = readingMinutes(htmlToText(html));
  const toc = headings.length >= 2 && (
    <nav aria-label="Daftar isi" className="rounded-lg border border-line bg-white p-4 text-sm">
      <p className="mb-2 font-semibold text-ink">Daftar isi</p>
      <ol className="m-0 flex list-none flex-col gap-1.5 p-0">
        {headings.map((heading) => (
          <li key={heading.id} className={heading.level === 3 ? 'pl-3' : undefined}>
            <a href={`#${heading.id}`} className="text-ink-subtle hover:text-primary">{heading.text}</a>
          </li>
        ))}
      </ol>
    </nav>
  );
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_240px] lg:items-start">
      <article className="min-w-0 rounded-lg border border-line-subtle bg-white px-5 py-6 md:px-10 md:py-8">
        <p className="mb-6 flex flex-wrap gap-x-3 gap-y-1 text-sm text-muted">
          {section?.name && <span>{section.name}</span>}
          <span>± {minutes} menit baca</span>
        </p>
        {toc && <div className="mb-6 lg:hidden">{toc}</div>}
        <MoodleHtml html={anchored} className="prose-article mx-auto max-w-[72ch]" />
        <div className="mt-10 border-t border-line-subtle pt-4">
          <Link to={`/course/${course.id}${section ? `#section-${section.section}` : ''}`} className="font-semibold">
            ← Kembali ke {section?.name ?? 'kursus'}
          </Link>
        </div>
      </article>
      {toc && <aside className="hidden lg:sticky lg:top-4 lg:block">{toc}</aside>}
    </div>
  );
}

function AssignContent({ course, mod, renderAssign }) {
  const { data, error, loading } = useApi(() => getAssignments([course.id]), [course.id]);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;
  const assign = data.find((a) => String(a.cmid) === String(mod.id));
  // Tanpa sesi Moodle di browser: tampilkan instruksi tugas dari Backend Gateway.
  if (!assign && mod.description) {
    return (
      <Card>
        <MoodleHtml html={mod.description} />
      </Card>
    );
  }
  if (!assign) return <EmptyState title="Instruksi tugas belum tersedia." />;

  return (
    <div>
      <AssignIntro assign={assign} />
      {renderAssign(assign, mod)}
    </div>
  );
}

function ExternalContent({ mod }) {
  const files = (mod.contents ?? []).filter((f) => f.fileurl);
  return (
    <Card>
      <MoodleHtml html={mod.description} />
      {mod.modname === 'url' && (
        <p className="mt-3">
          Klik{' '}
          <a href={files[0]?.fileurl ?? mod.url} target="_blank" rel="noreferrer">
            {files[0]?.fileurl ?? mod.url}
          </a>{' '}
          untuk membuka tautan.
        </p>
      )}
      {mod.modname !== 'url' && files.length > 0 && (
        <ul className="list mt-3">
          {files.map((f) => (
            <li key={f.fileurl} className="list__split">
              <span>{f.filename}</span>
              <a href={withToken(f.fileurl)} target="_blank" rel="noreferrer" className="btn btn--sm">
                Unduh
              </a>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/**
 * Halaman aktivitas yang sama untuk dosen dan mahasiswa: breadcrumb, judul, tanggal, dan isi
 * halaman/tautan/file. Bagian bawah tugas berbeda per peran dan dirender lewat `renderAssign(assign, mod)`.
 * Dosen dapat meneruskan `headerActions` dan `beforeContent` (mis. kontrol regenerasi konten AI).
 */
export default function ActivityView({ renderAssign, headerActions = null, beforeContent = null }) {
  const { cmid } = useParams();
  const { course, sections, reload } = useMoodleCourse();
  const section = sections.find((s) => (s.modules ?? []).some((m) => String(m.id) === String(cmid)));
  const mod = section?.modules?.find((m) => String(m.id) === String(cmid));
  useCourseBreadcrumb(mod ? [{ label: section.name, to: `/course/${course.id}#section-${section.section}` }, { label: mod.name }] : []);

  // Activity baru (mis. hasil eksekusi Generator AI) belum ada di isi kursus yang dimuat sebelumnya: ambil ulang
  // sekali sebelum menyimpulkan activity tidak ada.
  const lookupKey = `${course.id}:${cmid}`;
  const retried = useRef(null);
  const [retryDone, setRetryDone] = useState(null);
  useEffect(() => {
    if (mod || !reload || retried.current === lookupKey) return;
    retried.current = lookupKey;
    Promise.resolve(reload({ silent: true })).finally(() => setRetryDone(lookupKey));
  }, [mod, reload, lookupKey]);

  if (!mod && reload && retryDone !== lookupKey) return <Spinner label="Memuat aktivitas…" />;

  if (!mod) {
    return (
      <EmptyState title="Aktivitas tidak ditemukan." action={<Link to={`/course/${course.id}`}>Kembali ke kursus</Link>} />
    );
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <ActivityIcon modname={mod.modname} src={mod.modicon} />
          <h2 className="text-2xl wrap-anywhere">{mod.name}</h2>
        </div>
        {headerActions && <div className="flex flex-wrap items-center gap-2">{headerActions}</div>}
      </div>
      {beforeContent}
      {mod.dates?.length > 0 && mod.modname !== 'assign' && (
        <div className="mb-3 flex flex-wrap gap-x-6 text-sm">
          {mod.dates.map((d) => (
            <span key={d.label}>
              <strong>{d.label}</strong> {formatUnixDateTime(d.timestamp)}
            </span>
          ))}
        </div>
      )}

      {mod.modname === 'page' ? (
        <PageContent course={course} mod={mod} section={section} />
      ) : mod.modname === 'assign' ? (
        <AssignContent course={course} mod={mod} renderAssign={renderAssign} />
      ) : (
        <ExternalContent mod={mod} />
      )}
    </div>
  );
}
