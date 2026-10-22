import { useId, useState } from 'react';
import { ErrorAlert, Field } from '../../ui';
import ActivityFormActions from './ActivityFormActions';

const MAX_LENGTH = 5000;

/** Formulir Teks dan media (mod_label): teks yang tampil langsung di halaman kursus. */
export default function TextMediaForm({ canCreate, moodleHref, pending, error, onSubmit, onBack }) {
  const id = useId();
  const [text, setText] = useState('');
  const [fieldError, setFieldError] = useState(null);

  const submit = (event) => {
    event.preventDefault();
    if (!text.trim()) {
      setFieldError('Isi teks wajib diisi.');
      return;
    }
    onSubmit({ text: text.trim() });
  };

  return (
    <form className="form" onSubmit={submit} noValidate>
      <ErrorAlert error={error} />
      <Field
        label="Isi"
        required
        error={fieldError}
        errorId={`${id}-text`}
        hint={`${text.length} / ${MAX_LENGTH} karakter. Baris kosong memisahkan paragraf.`}
      >
        <textarea
          rows={6}
          value={text}
          maxLength={MAX_LENGTH}
          autoFocus
          disabled={!canCreate}
          aria-invalid={fieldError ? 'true' : undefined}
          aria-describedby={fieldError ? `${id}-text` : undefined}
          className={fieldError ? 'border-danger focus:border-danger focus:ring-danger/20' : undefined}
          onChange={(event) => {
            setText(event.target.value);
            if (fieldError && event.target.value.trim()) setFieldError(null);
          }}
        />
      </Field>
      {!canCreate && (
        <p className="text-sm text-muted">Moodle belum menyediakan layanan untuk membuat teks dan media dari aplikasi; lanjutkan pengisian di Moodle.</p>
      )}
      <ActivityFormActions canCreate={canCreate} moodleHref={moodleHref} pending={pending} submitLabel="Simpan" onBack={onBack} />
    </form>
  );
}
