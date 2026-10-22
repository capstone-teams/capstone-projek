import { useId, useState } from 'react';
import { ErrorAlert, Field } from '../../ui';
import ActivityFormActions from './ActivityFormActions';

const toUnix = (value) => (value ? Math.floor(new Date(value).getTime() / 1000) : 0);

function validate(form) {
  const errors = {};
  if (!form.name.trim()) errors.name = 'Nama tugas wajib diisi.';
  const grade = Number(form.grade);
  if (!Number.isInteger(grade) || grade < 1 || grade > 100) errors.grade = 'Nilai maksimum harus bilangan bulat 1–100.';
  if (form.opens && form.due && toUnix(form.due) <= toUnix(form.opens)) errors.due = 'Tenggat harus setelah tanggal dibuka.';
  return errors;
}

/** Formulir Tugas (mod_assign): nama, deskripsi, tanggal dibuka, tenggat, dan nilai maksimum. */
export default function AssignmentForm({ canCreate, moodleHref, pending, error, onSubmit, onBack }) {
  const id = useId();
  const [form, setForm] = useState({ name: '', intro: '', opens: '', due: '', grade: '100' });
  const [errors, setErrors] = useState({});

  const update = (key) => (event) => {
    setForm((current) => ({ ...current, [key]: event.target.value }));
    if (errors[key]) setErrors((current) => ({ ...current, [key]: undefined }));
  };
  const invalid = (key) =>
    errors[key]
      ? { 'aria-invalid': 'true', 'aria-describedby': `${id}-${key}`, className: 'border-danger focus:border-danger focus:ring-danger/20' }
      : {};

  const submit = (event) => {
    event.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    const intro = form.intro.trim();
    onSubmit({
      name: form.name.trim(),
      intro: intro ? `<p>${intro.replace(/[&<>]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[ch]).replace(/\n/g, '<br>')}</p>` : '',
      allowsubmissionsfromdate: toUnix(form.opens),
      duedate: toUnix(form.due),
      grade: Number(form.grade),
    });
  };

  return (
    <form className="form" onSubmit={submit} noValidate>
      <ErrorAlert error={error} />
      <Field label="Nama tugas" required error={errors.name} errorId={`${id}-name`}>
        <input value={form.name} maxLength={255} onChange={update('name')} autoFocus disabled={!canCreate} {...invalid('name')} />
      </Field>
      <Field label="Deskripsi" hint="Instruksi pengerjaan yang dilihat mahasiswa.">
        <textarea rows={3} value={form.intro} onChange={update('intro')} disabled={!canCreate} />
      </Field>
      <div className="grid grid-cols-2 gap-3 max-phone:grid-cols-1">
        <Field label="Dibuka">
          <input type="datetime-local" value={form.opens} onChange={update('opens')} disabled={!canCreate} />
        </Field>
        <Field label="Tenggat" error={errors.due} errorId={`${id}-due`}>
          <input type="datetime-local" value={form.due} onChange={update('due')} disabled={!canCreate} {...invalid('due')} />
        </Field>
      </div>
      <Field label="Nilai maksimum" required error={errors.grade} errorId={`${id}-grade`}>
        <input type="number" min={1} max={100} step={1} value={form.grade} onChange={update('grade')} disabled={!canCreate} {...invalid('grade')} />
      </Field>
      {!canCreate && (
        <p className="text-sm text-muted">Moodle belum menyediakan layanan untuk membuat tugas dari aplikasi; lanjutkan pengisian di Moodle.</p>
      )}
      <ActivityFormActions canCreate={canCreate} moodleHref={moodleHref} pending={pending} submitLabel="Simpan tugas" onBack={onBack} />
    </form>
  );
}
