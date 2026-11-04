import { useState } from 'react';
import { useApi } from '../../../hooks/useApi';
import { listAssignParticipants } from '../../../services/moodle/moodleApi';
import { Badge, Card, ErrorAlert, Spinner } from '../../../components/ui';
import ActivityView from '../../../components/moodle/course/ActivityView';

function timeRemaining(due, now) {
  if (!due) return '-';
  const diff = due - now;
  const abs = Math.abs(diff);
  const days = Math.floor(abs / 86400);
  const hours = Math.floor((abs % 86400) / 3600);
  const text = `${days} hari ${hours} jam`;
  return diff >= 0 ? text : `Lewat ${text}`;
}

/** Ringkasan pengumpulan tugas untuk dosen: jumlah peserta, sudah mengumpulkan, dan perlu dinilai. */
function TeacherSummary({ assign }) {
  // Waktu saat halaman dibuka, untuk menghitung sisa waktu tenggat.
  const [now] = useState(() => Math.floor(Date.now() / 1000));
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

/** Aktivitas untuk dosen: tugas menampilkan ringkasan pengumpulan seluruh mahasiswa. */
export default function ActivityPage() {
  return <ActivityView renderAssign={(assign) => <TeacherSummary assign={assign} />} />;
}
