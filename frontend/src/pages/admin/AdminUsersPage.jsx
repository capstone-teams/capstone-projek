import { useMemo, useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { getUser, listUsers } from '../../services/adminService';
import { PageContainer } from '../../components/layout/MoodleLayout';
import { Badge, Card, EmptyState, ErrorAlert, Spinner } from '../../components/ui';
import { formatDateTime } from '../../utils/format';

const ROLE_LABELS = { INSTRUCTOR: 'Dosen', STUDENT: 'Mahasiswa', ADMIN: 'Admin' };
const STATUS_META = { ACTIVE: { label: 'Aktif', tone: 'success' }, INACTIVE: { label: 'Nonaktif', tone: 'neutral' } };
const fullName = (user) => `${user.firstname ?? ''} ${user.lastname ?? ''}`.trim() || user.username;

/** Detail satu pengguna dari GET /admin/users/{id}. */
function UserDetail({ userId }) {
  const { data, error, loading } = useApi(() => getUser(userId), [userId]);
  if (loading && !data) return <Spinner label="Memuat detail pengguna…" />;
  if (error) return <ErrorAlert error={error} />;
  const status = STATUS_META[data.status] ?? { label: data.status, tone: 'neutral' };
  return (
    <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm" aria-label="Detail pengguna">
      <dt className="text-muted">Nama</dt><dd>{fullName(data)}</dd>
      <dt className="text-muted">Username</dt><dd className="wrap-anywhere">{data.username}</dd>
      <dt className="text-muted">Email</dt><dd className="wrap-anywhere">{data.email}</dd>
      <dt className="text-muted">Peran</dt><dd>{ROLE_LABELS[data.role] ?? data.role}</dd>
      <dt className="text-muted">Status</dt><dd><Badge tone={status.tone}>{status.label}</Badge></dd>
      <dt className="text-muted">Dibuat</dt><dd>{formatDateTime(data.created_at)}</dd>
    </dl>
  );
}

/** Daftar pengguna untuk admin (GET /admin/users), dengan pencarian, filter peran, dan detail. */
export default function AdminUsersPage() {
  const { data, error, loading, reload } = useApi(listUsers, []);
  const [query, setQuery] = useState('');
  const [role, setRole] = useState('');
  const [selected, setSelected] = useState(null);

  const users = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data ?? []).filter((user) => (!role || user.role === role)
      && (!q || [user.username, user.email, fullName(user)].some((value) => value?.toLowerCase().includes(q))));
  }, [data, query, role]);

  return (
    <PageContainer>
      <h1 className="moodle-h1 mb-4">Pengguna</h1>
      <div className="grid grid--2">
        <Card title="Daftar pengguna">
          {error && (
            <div className="mb-3">
              <ErrorAlert error={error} />
              <button type="button" className="btn" onClick={() => reload()}>Coba lagi</button>
            </div>
          )}
          <div className="mb-3 flex flex-wrap gap-2">
            <input type="search" className="min-w-0 flex-1" placeholder="Cari nama, username, atau email" aria-label="Cari pengguna" value={query} onChange={(e) => setQuery(e.target.value)} />
            <select aria-label="Filter peran" className="w-auto!" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="">Semua peran</option>
              {Object.entries(ROLE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </div>
          {loading && !data ? (
            <Spinner label="Memuat pengguna…" />
          ) : !users.length ? (
            !error && <EmptyState title="Tidak ada pengguna." />
          ) : (
            <ul className="m-0 flex list-none flex-col gap-2 p-0" aria-label="Daftar pengguna">
              {users.map((user) => (
                <li key={user.id}>
                  <button
                    type="button"
                    aria-current={selected === user.id ? 'true' : undefined}
                    onClick={() => setSelected(user.id)}
                    className={`flex w-full cursor-pointer items-center justify-between gap-3 rounded-lg border p-3 text-left ${selected === user.id ? 'border-primary bg-primary-light' : 'border-line bg-white hover:bg-surface'}`}
                  >
                    <span className="min-w-0">
                      <span className="block font-semibold wrap-anywhere">{fullName(user)}</span>
                      <span className="block text-sm text-muted wrap-anywhere">{user.username} · {user.email}</span>
                    </span>
                    <Badge tone="info">{ROLE_LABELS[user.role] ?? user.role}</Badge>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Detail pengguna">
          {selected ? <UserDetail userId={selected} /> : <p className="text-sm text-muted">Pilih pengguna untuk melihat detailnya.</p>}
        </Card>
      </div>
    </PageContainer>
  );
}
