import { useState } from 'react';
import { getProfile, updateProfile } from '../../services/profileService';
import { useAction, useApi } from '../../hooks/useApi';
import { Alert, Card, ErrorAlert, Field, PageHeader, Spinner } from '../../components/ui';
import { useAuth } from '../../hooks/useAuth';
import { formatDateTime } from '../../utils/format';

const LANGUAGES = ['Bahasa Indonesia', 'English', 'Bilingual (ID/EN)'];

function ProfileForm({ initial, onSaved }) {
  const [form, setForm] = useState({
    teaching_style: initial.teaching_style ?? '',
    language_preference: initial.language_preference ?? LANGUAGES[0],
    content_preference: initial.content_preference ?? '',
  });
  const [saved, setSaved] = useState(false);
  const save = useAction(updateProfile);

  const update = (key) => (e) => {
    setSaved(false);
    setForm((f) => ({ ...f, [key]: e.target.value }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    const data = await save.run(form).catch(() => null);
    if (data) {
      setSaved(true);
      onSaved(data);
    }
  };

  return (
    <form onSubmit={onSubmit} className="form">
      <ErrorAlert error={save.error} onClose={save.clearError} />
      {saved && <Alert tone="success">Profil tersimpan.</Alert>}

      <Field label="Gaya mengajar" hint="Contoh: interaktif, berbasis proyek, banyak studi kasus.">
        <textarea rows={3} value={form.teaching_style} onChange={update('teaching_style')} />
      </Field>
      <Field label="Bahasa konten">
        <select value={form.language_preference} onChange={update('language_preference')}>
          {LANGUAGES.map((l) => (
            <option key={l}>{l}</option>
          ))}
        </select>
      </Field>
      <Field label="Preferensi konten" hint="Contoh: materi ringkas, banyak contoh kode, sertakan video.">
        <textarea rows={3} value={form.content_preference} onChange={update('content_preference')} />
      </Field>

      <div className="form__actions">
        <button type="submit" className="btn btn--primary" disabled={save.pending}>
          {save.pending ? 'Menyimpan…' : 'Simpan profil'}
        </button>
      </div>
    </form>
  );
}

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
          {loading && !data ? <Spinner /> : data && <ProfileForm initial={data} onSaved={setData} />}
        </Card>
      </div>
    </>
  );
}
