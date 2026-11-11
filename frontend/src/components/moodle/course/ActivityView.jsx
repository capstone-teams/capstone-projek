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

function PageContent({ course, mod }) {
  const { data, error, loading } = useApi(() => getPages([course.id]), [course.id]);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;
  const page = data.find((p) => String(p.coursemodule) === String(mod.id));
  // Lewat Backend Gateway isi Page sudah ikut di modul (GET /integrations/moodle/courses/{id}/contents).
  const html = page?.content ?? mod.content;
  if (!html) return <EmptyState title="Halaman tidak ditemukan." />;
  return (
    <Card>
      <MoodleHtml html={html} />
    </Card>
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
  if (!assign) return <EmptyState title="Tugas tidak ditemukan." />;

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
  const { course, sections } = useMoodleCourse();
  const section = sections.find((s) => (s.modules ?? []).some((m) => String(m.id) === String(cmid)));
  const mod = section?.modules?.find((m) => String(m.id) === String(cmid));
  useCourseBreadcrumb(mod ? [{ label: section.name, to: `/course/${course.id}#section-${section.section}` }, { label: mod.name }] : []);

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
        <PageContent course={course} mod={mod} />
      ) : mod.modname === 'assign' ? (
        <AssignContent course={course} mod={mod} renderAssign={renderAssign} />
      ) : (
        <ExternalContent mod={mod} />
      )}
    </div>
  );
}
