import { useId, useState } from 'react';
import { ErrorAlert, Field } from '../../ui';
import ActivityFormActions from './ActivityFormActions';

const toUnix = (value) => (value ? Math.floor(new Date(value).getTime() / 1000) : 0);
const escapeHtml = (text) => text.replace(/[&<>]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[ch]);

// Tugas dan Quiz sama-sama punya nama, deskripsi, waktu buka, dan waktu tutup; Tugas juga punya nilai maksimum.
const ASSIGNMENT = {
  noun: 'tugas',
  nameLabel: 'Nama tugas',
  introHint: 'Instruksi pengerjaan yang dilihat mahasiswa.',
  closeLabel: 'Tenggat',
  closeError: 'Tenggat harus setelah tanggal dibuka.',
  submitLabel: 'Simpan tugas',
  withGrade: true,
  toFields: (form, intro) => ({
    name: form.name.trim(),
    intro,
    allowsubmissionsfromdate: toUnix(form.opens),
    duedate: toUnix(form.closes),
    grade: Number(form.grade),
  }),
};

const QUIZ = {
  noun: 'kuis',
  nameLabel: 'Nama kuis',
  introHint: 'Petunjuk pengerjaan yang dilihat mahasiswa.',
  closeLabel: 'Ditutup',
  closeError: 'Waktu ditutup harus setelah waktu dibuka.',
  submitLabel: 'Simpan kuis',
  withGrade: false,
  toFields: (form, intro) => ({ name: form.name.trim(), intro, timeopen: toUnix(form.opens), timeclose: toUnix(form.closes) }),
};

function validate(form, config) {
  const errors = {};
  if (!form.name.trim()) errors.name = `${config.nameLabel} wajib diisi.`;
  if (config.withGrade) {
    const grade = Number(form.grade);
    if (!Number.isInteger(grade) || grade < 1 || grade > 100) errors.grade = 'Nilai maksimum harus bilangan bulat 1–100.';
  }
  if (form.opens && form.closes && toUnix(form.closes) <= toUnix(form.opens)) errors.closes = config.closeError;
  return errors;
}

function DatedActivityForm({ config, canCreate, moodleHref, pending, error, onSubmit, onBack }) {
  const id = useId();
  const [form, setForm] = useState({ name: '', intro: '', opens: '', closes: '', grade: '100' });
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
    const found = validate(form, config);
    setErrors(found);
    if (Object.keys(found).length) return;
    const intro = form.intro.trim();
    onSubmit(config.toFields(form, intro ? `<p>${escapeHtml(intro).replace(/\n/g, '<br>')}</p>` : ''));
  };

  return (
    <form className="form" onSubmit={submit} noValidate>
      <ErrorAlert error={error} />
      <Field label={config.nameLabel} required error={errors.name} errorId={`${id}-name`}>
        <input value={form.name} maxLength={255} onChange={update('name')} autoFocus disabled={!canCreate} {...invalid('name')} />
      </Field>
      <Field label="Deskripsi" hint={config.introHint}>
        <textarea rows={3} value={form.intro} onChange={update('intro')} disabled={!canCreate} />
      </Field>
      <div className="grid grid-cols-2 gap-3 max-phone:grid-cols-1">
        <Field label="Dibuka">
          <input type="datetime-local" value={form.opens} onChange={update('opens')} disabled={!canCreate} />
        </Field>
        <Field label={config.closeLabel} error={errors.closes} errorId={`${id}-closes`}>
          <input type="datetime-local" value={form.closes} onChange={update('closes')} disabled={!canCreate} {...invalid('closes')} />
        </Field>
      </div>
      {config.withGrade && (
        <Field label="Nilai maksimum" required error={errors.grade} errorId={`${id}-grade`}>
          <input type="number" min={1} max={100} step={1} value={form.grade} onChange={update('grade')} disabled={!canCreate} {...invalid('grade')} />
        </Field>
      )}
      {!canCreate && (
        <p className="text-sm text-muted">Moodle belum menyediakan layanan untuk membuat {config.noun} dari aplikasi; lanjutkan pengisian di Moodle.</p>
      )}
      <ActivityFormActions canCreate={canCreate} moodleHref={moodleHref} pending={pending} submitLabel={config.submitLabel} onBack={onBack} />
    </form>
  );
}

export const AssignmentForm = (props) => <DatedActivityForm config={ASSIGNMENT} {...props} />;
export const QuizForm = (props) => <DatedActivityForm config={QUIZ} {...props} />;
