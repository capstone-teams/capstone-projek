import { useState } from 'react';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useApi } from '../../../hooks/useApi';
import { getEnrolledUsers } from '../../../services/moodle/moodleApi';
import { Avatar, Badge, ErrorAlert, Spinner } from '../../../components/ui';
import { formatRelative } from '../../../utils/format';

const ROLE_LABELS = {
  editingteacher: 'Dosen',
  teacher: 'Dosen (non-editing)',
  student: 'Mahasiswa',
  manager: 'Manager',
};

export default function ParticipantsPage() {
  const { course, isTeacher } = useMoodleCourse();
  const { data, error, loading } = useApi(() => getEnrolledUsers(course.id), [course.id]);
  const [query, setQuery] = useState('');
  const [role, setRole] = useState('');

  const q = query.trim().toLowerCase();
  const users = (data ?? []).filter(
    (u) =>
      (!q || `${u.fullname} ${u.email ?? ''}`.toLowerCase().includes(q)) &&
      (!role || u.roles?.some((r) => r.shortname === role)),
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input className="!w-full sm:!w-64" type="search" placeholder="Cari peserta" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Cari peserta" />
        <select className="!w-auto" value={role} onChange={(e) => setRole(e.target.value)} aria-label="Filter peran">
          <option value="">Semua peran</option>
          {Object.entries(ROLE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <span className="ml-auto text-sm text-muted">{data ? `${users.length} peserta` : ''}</span>
      </div>

      <ErrorAlert error={error} />
      {loading && !data ? (
        <Spinner />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Nama</th>
                {isTeacher && <th>Email</th>}
                <th>Peran</th>
                <th>Terakhir mengakses kursus</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>
                    <div className="flex items-center gap-2.5">
                      <Avatar name={u.fullname} src={u.profileimageurl} size="sm" />
                      <span>{u.fullname}</span>
                    </div>
                  </td>
                  {isTeacher && <td>{u.email || '-'}</td>}
                  <td>
                    <div className="chips">
                      {u.roles?.map((r) => (
                        <Badge key={r.shortname} tone={r.shortname === 'student' ? 'neutral' : 'info'}>
                          {ROLE_LABELS[r.shortname] ?? r.name ?? r.shortname}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td>{formatRelative(u.lastcourseaccess)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
