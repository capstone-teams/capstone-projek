import { getProfile } from '../../services/profileService';
import { useApi } from '../../hooks/useApi';
import { Card, ErrorAlert, PageHeader, Spinner } from '../../components/ui';
import TeachingProfileForm from '../../components/ai/TeachingProfileForm';
import { useAuth } from '../../hooks/useAuth';
import { formatDateTime } from '../../utils/format';

export default function TeachingProfilePage() {
  const { user } = useAuth();
  const { data, error, loading, setData } = useApi(getProfile);

  return (
    <>
      <PageHeader title="Profil Dosen" subtitle="Preferensi ini dipakai agent saat menyusun rencana dan konten." />
      <div className="grid grid--2">
        <Card title="Akun Moodle">
          <dl className="dl">
            <dt>Nama</dt>
            <dd>{user?.fullname}</dd>
            <dt>Username Moodle</dt>
            <dd>{user?.username}</dd>
            <dt>Peran</dt>
            <dd>Dosen</dd>
            {data?.updated_at && (
              <>
                <dt>Profil diperbarui</dt>
                <dd>{formatDateTime(data.updated_at)}</dd>
              </>
            )}
          </dl>
        </Card>
        <Card title="Preferensi mengajar">
          <ErrorAlert error={error} />
          {loading && !data ? <Spinner /> : data && <TeachingProfileForm initial={data} onSaved={setData} />}
        </Card>
      </div>
    </>
  );
}
