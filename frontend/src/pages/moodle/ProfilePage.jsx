import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import { getCoursesByClassification, getUserById } from '../../services/moodle/moodleApi';
import { moodleUrl } from '../../services/moodle/moodleClient';
import { PageContainer } from '../../components/MoodleLayout';
import { Avatar, Badge, Card, ErrorAlert, Spinner } from '../../components/ui';
import { formatUnixDateTime } from '../../utils/format';

export default function ProfilePage() {
  const { user, site } = useAuth();
  const profile = useApi(() => getUserById(user.id), [user.id]);
  const courses = useApi(() => getCoursesByClassification('all'));
  const p = profile.data;
  const teacherIds = new Set(user.teacherCourseIds);

  return (
    <PageContainer>
      <div className="mb-6 flex flex-wrap items-center gap-4">
        <Avatar name={user.fullname} src={user.avatar} size="lg" />
        <div>
          <h1 className="moodle-h1">{user.fullname}</h1>
          <div className="mt-1 flex flex-wrap gap-2">
            <Badge tone={user.role === 'dosen' ? 'info' : 'success'}>{user.role === 'dosen' ? 'Dosen' : 'Mahasiswa'}</Badge>
            {user.isAdmin && <Badge tone="warning">Admin situs</Badge>}
          </div>
        </div>
      </div>

      <div className="grid--2">
        <Card
          title="Detail pengguna"
          actions={
            <a href={moodleUrl(`/user/edit.php?id=${user.id}`)} target="_blank" rel="noreferrer" className="text-sm">
              Edit profil di Moodle ↗
            </a>
          }
        >
          <ErrorAlert error={profile.error} />
          {profile.loading && !p ? (
            <Spinner />
          ) : (
            <dl className="dl">
              <dt>Username</dt>
              <dd>{user.username}</dd>
              <dt>Email</dt>
              <dd>{p?.email || '-'}</dd>
              <dt>Kota</dt>
              <dd>{p?.city || '-'}</dd>
              <dt>Akses pertama</dt>
              <dd>{formatUnixDateTime(p?.firstaccess)}</dd>
              <dt>Akses terakhir</dt>
              <dd>{formatUnixDateTime(p?.lastaccess)}</dd>
              <dt>Situs</dt>
              <dd>{site?.name}</dd>
            </dl>
          )}
        </Card>
        <Card title="Detail kursus">
          <ErrorAlert error={courses.error} />
          {courses.loading && !courses.data ? (
            <Spinner />
          ) : (
            <ul className="list">
              {(courses.data ?? []).map((c) => (
                <li key={c.id} className="list__split">
                  <Link to={`/course/${c.id}`}>{c.fullname}</Link>
                  <Badge tone={teacherIds.has(c.id) ? 'info' : 'neutral'}>{teacherIds.has(c.id) ? 'Dosen' : 'Mahasiswa'}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </PageContainer>
  );
}
