import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useApi } from '../../../hooks/useApi';
import { getAssignments, getPages, getSubmissionStatus, listAssignParticipants } from '../../../services/moodle/moodleApi';
import { moodleUrl, withToken } from '../../../services/moodle/moodleClient';
import { Badge, Card, EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import ActivityIcon from '../../../components/moodle/ActivityIcon';
import MoodleHtml from '../../../components/moodle/MoodleHtml';
import { formatUnixDateTime } from '../../../utils/format';

const SUBMISSION_STATUS = {
  new: ['Belum ada pengumpulan', 'neutral'],
  draft: ['Draft (belum dikirim)', 'warning'],
  submitted: ['Sudah dikumpulkan untuk dinilai', 'success'],
  reopened: ['Dibuka kembali', 'warning'],
};
const GRADING_STATUS = {
  notgraded: 'Belum dinilai',
  graded: 'Sudah dinilai',
  released: 'Nilai dirilis',
};

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

function StudentSubmission({ assign }) {
  const now = useNow();
  const { data, error, loading } = useApi(() => getSubmissionStatus(assign.id), [assign.id]);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;

  const attempt = data.lastattempt ?? {};
  const status = attempt.submission?.status ?? attempt.teamsubmission?.status ?? 'new';
  const [statusLabel, statusTone] = SUBMISSION_STATUS[status] ?? [status, 'neutral'];
  const overdue = assign.duedate && assign.duedate < now && status !== 'submitted';

  const rows = [
    ['Status pengumpulan', <Badge tone={statusTone}>{statusLabel}</Badge>],
    ['Status penilaian', GRADING_STATUS[attempt.gradingstatus] ?? attempt.gradingstatus ?? '-'],
    ['Sisa waktu', <span className={overdue ? 'font-semibold text-danger' : ''}>{timeRemaining(assign.duedate, now)}</span>],
    ['Terakhir diubah', formatUnixDateTime(attempt.submission?.timemodified)],
  ];
  if (data.feedback?.gradefordisplay) rows.push(['Nilai', <MoodleHtml html={data.feedback.gradefordisplay} />]);

  return (
    <Card title="Status pengumpulan">
      <table className="table">
        <tbody>
          {rows.map(([label, value]) => (
            <tr key={label}>
              <th className="w-1/3 bg-surface !font-normal">{label}</th>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <a href={moodleUrl(`/mod/assign/view.php?id=${assign.cmid}`)} target="_blank" rel="noreferrer" className="btn btn--primary mt-4">
        {status === 'submitted' ? 'Lihat pengumpulan di Moodle' : 'Kumpulkan tugas di Moodle'} ↗
      </a>
    </Card>
  );
}

function TeacherSummary({ assign }) {
  const now = useNow();
  const { data, error, loading } = useApi(() => listAssignParticipants(assign.id), [assign.id]);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;

  const submitted = data.filter((p) => p.submitted).length;
  const needGrading = data.filter((p) => p.requiregrading).length;
  return (
    <Card
      title="Ringkasan penilaian"
      actions={
        <a href={moodleUrl(`/mod/assign/view.php?id=${assign.cmid}&action=grading`)} target="_blank" rel="noreferrer" className="btn btn--primary btn--sm">
          Nilai di Moodle ↗
        </a>
      }
    >
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
    <div className="stack">
      <Card>
        <div className="mb-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
          {assign.allowsubmissionsfromdate > 0 && (
            <span>
              <strong>Dibuka:</strong> {formatUnixDateTime(assign.allowsubmissionsfromdate)}
            </span>
          )}
          {assign.duedate > 0 && (
            <span>
              <strong>Tenggat:</strong> {formatUnixDateTime(assign.duedate)}
            </span>
          )}
        </div>
        <MoodleHtml html={assign.intro} />
      </Card>
      {isTeacher ? <TeacherSummary assign={assign} /> : <StudentSubmission assign={assign} />}
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
      {!['url', 'resource', 'folder'].includes(mod.modname) && (
        <a href={moodleUrl(mod.url)} target="_blank" rel="noreferrer" className="btn btn--primary mt-4">
          Buka aktivitas di Moodle ↗
        </a>
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
