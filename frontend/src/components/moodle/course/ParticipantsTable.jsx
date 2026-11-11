import { useState } from 'react';
import { useApi } from '../../../hooks/useApi';
import { addMoodleParticipant, getEnrolledUsers } from '../../../services/moodle/moodleApi';
import { Avatar, Badge, ErrorAlert, Field, Modal, Spinner } from '../../ui';
import { formatRelative } from '../../../utils/format';

const ROLE_LABELS = {
  editingteacher: 'Dosen',
  teacher: 'Dosen (non-editing)',
  student: 'Mahasiswa',
  manager: 'Manager',
};

/** Daftar peserta kursus dengan pencarian dan filter peran. `showEmail` dan `canManage` hanya untuk dosen. */
export default function ParticipantsTable({ courseId, showEmail = false, canManage = false }) {
  const { data, error, loading, reload } = useApi(() => getEnrolledUsers(courseId), [courseId]);
  const [query, setQuery] = useState('');
  const [role, setRole] = useState('');
  const [addOpen, setAddOpen] = useState(false);
  const [addQuery, setAddQuery] = useState('');
  const [addRole, setAddRole] = useState('student');
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState(null);

  const openAdd = () => {
    setAddQuery('');
    setAddRole('student');
    setAddError(null);
    setAddOpen(true);
  };

  // Akun dicari di Moodle lewat email atau username; dosen tidak membuat akun baru di sini.
  const submitAdd = async (event) => {
    event.preventDefault();
    setAdding(true);
    setAddError(null);
    try {
      await addMoodleParticipant(courseId, { query: addQuery, role: addRole });
      setAddOpen(false);
      await reload({ silent: true });
    } catch (caught) {
      setAddError(caught);
    } finally {
      setAdding(false);
    }
  };

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
        {canManage && (
          <button type="button" className="btn btn--primary btn--sm" onClick={openAdd}>
            Tambah peserta
          </button>
        )}
      </div>

      {canManage && (
        <Modal open={addOpen} title="Tambah peserta dari Moodle" onClose={() => setAddOpen(false)}>
          <form onSubmit={submitAdd} className="form">
            <p className="text-sm text-muted">
              Masukkan email atau username akun Moodle mahasiswa/dosen. Akun harus sudah ada di Moodle.
            </p>
            <Field label="Email atau username" required>
              <input
                value={addQuery}
                onChange={(e) => setAddQuery(e.target.value)}
                placeholder="nama@kampus.ac.id"
                aria-label="Email atau username Moodle"
                required
                autoFocus
              />
            </Field>
            <Field label="Peran">
              <select value={addRole} onChange={(e) => setAddRole(e.target.value)} aria-label="Peran peserta">
                <option value="student">Mahasiswa</option>
                <option value="teacher">Dosen</option>
              </select>
            </Field>
            <ErrorAlert error={addError} />
            <div className="flex justify-end gap-2">
              <button type="button" className="btn btn--ghost" onClick={() => setAddOpen(false)}>
                Batal
              </button>
              <button type="submit" className="btn btn--primary" disabled={adding || !addQuery.trim()}>
                {adding ? 'Menambahkan…' : 'Tambahkan'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      <ErrorAlert error={error} />
      {loading && !data ? (
        <Spinner />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Nama</th>
                {showEmail && <th>Email</th>}
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
                  {showEmail && <td>{u.email || '-'}</td>}
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
