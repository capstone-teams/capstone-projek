import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useApi } from '../../../hooks/useApi';
import { getAssignments, getPages, listAssignParticipants } from '../../../services/moodle/moodleApi';
import { withToken } from '../../../services/moodle/moodleClient';
import { Badge, Card, EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import ActivityIcon from '../../../components/moodle/ActivityIcon';
import MoodleHtml from '../../../components/moodle/MoodleHtml';
import AssignSubmission, { AssignIntro } from '../../../components/moodle/AssignSubmission';
import { formatUnixDateTime } from '../../../utils/format';

function timeRemaining(due, now) {
  if (!due) return '-';
  const diff = due - now;
  const abs = Math.abs(diff);
  const days = Math.floor(abs / 86400);
  const hours = Math.floor((abs % 86400) / 3600);
  const text = `${days} hari ${hours} jam`;
  return diff >= 0 ? text : `Lewat ${text}`;
}

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

// Waktu saat halaman dibuka, untuk menghitung sisa waktu tenggat.
function useNow() {
  const [now] = useState(() => Math.floor(Date.now() / 1000));
  return now;
}

function TeacherSummary({ assign }) {
  const now = useNow();
  const { data, error, loading } = useApi(() => listAssignParticipants(assign.id), [assign.id]);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;

  const submitted = data.filter((p) => p.submitted).length;
  const needGrading = data.filter((p) => p.requiregrading).length;
  return (
    <Card title="Ringkasan penilaian">
      <div className="stats">
        <div className="stat">
          <span className="stat__value">{data.length}</span>
          <span className="stat__label">Peserta</span>
        </div>
        <div className="stat">
          <span className="stat__value">{submitted}</span>
          <span className="stat__label">Sudah mengumpulkan</span>
        </div>
        <div className="stat">
          <span className="stat__value">{needGrading}</span>
          <span className="stat__label">Perlu dinilai</span>
        </div>
        <div className="stat">
          <span className="stat__value">{timeRemaining(assign.duedate, now)}</span>
          <span className="stat__label">Sisa waktu</span>
        </div>
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Mahasiswa</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.map((p) => (
              <tr key={p.id}>
                <td>{p.fullname}</td>
                <td>
                  <Badge tone={p.submitted ? 'success' : 'neutral'}>{p.submitted ? 'Sudah mengumpulkan' : 'Belum mengumpulkan'}</Badge>
                  {p.requiregrading && (
                    <span className="ml-2">
                      <Badge tone="warning">Perlu dinilai</Badge>
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function AssignContent({ course, mod, isTeacher }) {
  const { data, error, loading } = useApi(() => getAssignments([course.id]), [course.id]);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;
  const assign = data.find((a) => a.cmid === mod.id);
  if (!assign) return <EmptyState title="Tugas tidak ditemukan." />;

  return (
    <div>
      <AssignIntro assign={assign} />
      {isTeacher ? <TeacherSummary assign={assign} /> : <AssignSubmission assign={assign} editPath={`/course/${course.id}/mod/${mod.id}/editsubmission`} />}
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

export default function ActivityPage() {
  const { cmid } = useParams();
  const { course, sections, isTeacher } = useMoodleCourse();
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
        <AssignContent course={course} mod={mod} isTeacher={isTeacher} />
      ) : (
        <ExternalContent mod={mod} />
      )}
    </div>
  );
}
