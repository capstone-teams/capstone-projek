import { useState } from 'react';
import { updateProfile } from '../../services/profileService';
import { useAction } from '../../hooks/useApi';
import { Alert, ErrorAlert, Field } from '../ui';

const LANGUAGES = ['Bahasa Indonesia', 'English', 'Bilingual (ID/EN)'];

export default function TeachingProfileForm({ initial, onSaved }) {
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
