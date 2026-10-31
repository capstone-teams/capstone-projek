import { Link, useParams } from 'react-router-dom';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
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
  const page = data.find((p) => p.coursemodule === mod.id);
  if (!page) return <EmptyState title="Halaman tidak ditemukan." />;
  return (
    <Card>
      <MoodleHtml html={page.content} />
    </Card>
  );
}

function AssignContent({ course, mod, renderAssign }) {
  const { data, error, loading } = useApi(() => getAssignments([course.id]), [course.id]);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;
  const assign = data.find((a) => a.cmid === mod.id);
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
 */
export default function ActivityView({ renderAssign }) {
  const { cmid } = useParams();
  const { course, sections } = useMoodleCourse();
  const section = sections.find((s) => s.modules.some((m) => m.id === Number(cmid)));
  const mod = section?.modules.find((m) => m.id === Number(cmid));

  if (!mod) {
    return (
      <EmptyState title="Aktivitas tidak ditemukan." action={<Link to={`/course/${course.id}`}>Kembali ke kursus</Link>} />
    );
  }

  return (
    <div>
      <nav className="mb-3 text-sm text-muted" aria-label="Breadcrumb aktivitas">
        <Link to={`/course/${course.id}#section-${section.section}`}>{section.name}</Link>
      </nav>
      <div className="mb-4 flex items-center gap-3">
        <ActivityIcon modname={mod.modname} src={mod.modicon} />
        <h2 className="text-2xl">{mod.name}</h2>
      </div>
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
