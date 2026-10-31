import { useId, useRef, useState } from 'react';
import { ErrorAlert } from '../../ui';
import MoodleEditor from '../submission/MoodleEditor';
import { DateTimeSelector, FormRow, FormSection, FormSections } from './MoodleForm';
import { dateValue, toUnix } from '../../../utils/dateSelector';

/*
 * Formulir "New <aktivitas>" seperti course/modedit.php: field, bagian, default, dan pesan validasi
 * diambil dari mod/assign, mod/quiz, dan mod/label (mod_form.php dan lang/en). Hanya setelan yang
 * benar-benar disimpan yang ditampilkan.
 */

const REQUIRED = 'You must supply a value here.';
const MB = 1024 * 1024;
const MAX_SIZES = [1, 2, 5, 10, 20, 50].map((n) => n * MB);
const MAX_GRADE = 100;
const plain = (html) => new DOMParser().parseFromString(html, 'text/html').body.textContent.trim();

function useFormState(initial) {
  const [form, setForm] = useState(initial);
  const [errors, setErrors] = useState({});
  const set = (key) => (value) => {
    setForm((current) => ({ ...current, [key]: value }));
    if (errors[key]) setErrors((current) => ({ ...current, [key]: undefined }));
  };
  return { form, set, errors, setErrors };
}

function NameField({ id, label, value, onChange, error, required = true }) {
  return (
    <FormRow label={label} labelFor={id} required={required} error={error} errorId={`${id}-error`}>
      <input
        id={id}
        value={value}
        maxLength={1333}
        autoFocus
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className={error ? 'border-danger' : undefined}
        onChange={(event) => onChange(event.target.value)}
      />
    </FormRow>
  );
}

function EditorField({ id, label, required, value, onChange, error }) {
  return (
    <FormRow label={label} labelId={`${id}-label`} required={required} error={error} errorId={`${id}-error`}>
      <MoodleEditor id={id} labelId={`${id}-label`} initialValue={value} onChange={onChange} invalid={!!error} describedBy={error ? `${id}-error` : undefined} />
    </FormRow>
  );
}

/** Tombol bawah modedit.php; tanpa API pembuatan dari backend, simpan dinonaktifkan. */
function ModFormButtons({ canCreate, pending, withDisplay, onCancel, onSave }) {
  return (
    <div className="mt-6 grid gap-x-6 md:grid-cols-[minmax(0,1fr)_minmax(0,3fr)]">
      <div className="flex flex-wrap gap-2 md:col-start-2">
        <button type="submit" className="btn btn--primary" disabled={pending || !canCreate} onClick={() => onSave(false)}>Save and return to course</button>
        {withDisplay && <button type="submit" className="btn btn--primary" disabled={pending || !canCreate} onClick={() => onSave(true)}>Save and display</button>}
        <button type="button" className="btn btn--secondary" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

function ModForm({ sections, initiallyOpen, validate, toFields, state, props, withDisplay = true, children }) {
  // Tombol yang menekan submit (Save and display atau Save and return), dibaca pada event yang sama.
  const displayRef = useRef(false);
  const submit = (event) => {
    event.preventDefault();
    const found = validate(state.form);
    state.setErrors(found);
    if (Object.values(found).some(Boolean)) {
      // Seperti Moodle: buka bagian yang berisi error lalu fokus ke field pertama yang salah.
      const form = event.currentTarget;
      setTimeout(() => {
        const field = form.querySelector('[aria-invalid="true"], [data-invalid="true"]');
        const body = field?.closest('[hidden]');
        if (body) form.querySelector(`[aria-controls="${body.id}"]`)?.click();
        setTimeout(() => (field?.matches('input, select, textarea, [contenteditable]') ? field : field?.querySelector('select, input'))?.focus());
      });
      return;
    }
    props.onSubmit(toFields(state.form), displayRef.current);
    displayRef.current = false;
  };
  return (
    <form onSubmit={submit} noValidate>
      <ErrorAlert error={props.error} />
      {!props.canCreate && (
        <p className="mb-3 text-sm text-muted">Pembuatan aktivitas belum tersedia di API backend, sehingga formulir ini belum dapat disimpan.</p>
      )}
      <FormSections ids={sections} initiallyOpen={initiallyOpen}>{children}</FormSections>
      <ModFormButtons
        canCreate={props.canCreate}
        pending={props.pending}
        withDisplay={withDisplay}
        onCancel={props.onCancel}
        onSave={(display) => { displayRef.current = display; }}
      />
      <p className="mt-4 text-sm text-muted">
        Required <span className="sr-only">fields are marked with</span>
        <span aria-hidden="true" className="ml-1 inline-grid size-4 place-items-center rounded-full bg-danger align-middle text-[10px] font-bold text-white">!</span>
      </p>
    </form>
  );
}

export function AssignModForm(props) {
  const id = useId();
  const state = useFormState({
    name: '', intro: '',
    opens: dateValue(0, true), due: dateValue(7, true), cutoff: dateValue(7, false),
    onlinetext: false, wordlimit: '', wordlimitEnabled: false,
    file: true, maxfiles: '20', maxbytes: String(MB),
    grade: '100',
  });
  const { form, set, errors } = state;
  const validate = (f) => {
    const found = {};
    if (!f.name.trim()) found.name = REQUIRED;
    if (f.opens.enabled && f.due.enabled && toUnix(f.due) < toUnix(f.opens)) found.due = 'Due date cannot be earlier than the allow submissions from date.';
    if (f.cutoff.enabled && f.due.enabled && toUnix(f.cutoff) < toUnix(f.due)) found.cutoff = 'Cut-off date cannot be earlier than the due date.';
    else if (f.cutoff.enabled && f.opens.enabled && toUnix(f.cutoff) < toUnix(f.opens)) found.cutoff = 'Cut-off date cannot be earlier than the allow submissions from date.';
    const limit = Number(f.wordlimit);
    if (f.onlinetext && f.wordlimitEnabled && (!Number.isInteger(limit) || limit < 1 || f.wordlimit === '')) found.wordlimit = 'You must enter a number here.';
    const grade = Number(f.grade);
    if (!Number.isInteger(grade) || grade < 1 || grade > MAX_GRADE) found.grade = `Invalid grade value. This must be an integer between 1 and ${MAX_GRADE}`;
    return found;
  };
  const toFields = (f) => ({
    name: f.name.trim(),
    intro: plain(f.intro) ? f.intro : '',
    allowsubmissionsfromdate: toUnix(f.opens),
    duedate: toUnix(f.due),
    cutoffdate: toUnix(f.cutoff),
    grade: Number(f.grade),
    // Nama setelan mengikuti plugin assignsubmission_onlinetext dan assignsubmission_file.
    onlinetext_enabled: f.onlinetext ? 1 : 0,
    onlinetext_wordlimit: f.onlinetext && f.wordlimitEnabled ? Number(f.wordlimit) : 0,
    file_enabled: f.file ? 1 : 0,
    file_maxfiles: Number(f.maxfiles),
    file_maxbytes: Number(f.maxbytes),
  });

  return (
    <ModForm sections={['general', 'availability', 'submissiontypes', 'grade']} initiallyOpen={['general', 'availability', 'submissiontypes']}
      validate={validate} toFields={toFields} state={state} props={props}
    >
      <FormSection id="general" title="General">
        <NameField id={`${id}-name`} label="Assignment name" value={form.name} onChange={set('name')} error={errors.name} />
        <EditorField id={`${id}-intro`} label="Description" value={form.intro} onChange={set('intro')} />
      </FormSection>
      <FormSection id="availability" title="Availability">
        <DateTimeSelector label="Allow submissions from" value={form.opens} onChange={set('opens')} />
        <DateTimeSelector label="Due date" value={form.due} onChange={set('due')} error={errors.due} />
        <DateTimeSelector label="Cut-off date" value={form.cutoff} onChange={set('cutoff')} error={errors.cutoff} />
      </FormSection>
      <FormSection id="submissiontypes" title="Submission types">
        <FormRow label="Submission types" labelId={`${id}-types`}>
          <div role="group" aria-labelledby={`${id}-types`} className="flex flex-wrap gap-x-6 gap-y-2 md:pt-2">
            <label className="flex items-center gap-1.5">
              <input type="checkbox" checked={form.onlinetext} onChange={(e) => set('onlinetext')(e.target.checked)} />
              Online text
            </label>
            <label className="flex items-center gap-1.5">
              <input type="checkbox" checked={form.file} onChange={(e) => set('file')(e.target.checked)} />
              File submissions
            </label>
          </div>
        </FormRow>
        {form.onlinetext && (
          <FormRow label="Word limit" labelFor={`${id}-wordlimit`} error={errors.wordlimit} errorId={`${id}-wordlimit-error`}>
            <div className="flex flex-wrap items-center gap-3">
              <input
                id={`${id}-wordlimit`}
                type="number"
                min={1}
                className="w-32!"
                value={form.wordlimit}
                disabled={!form.wordlimitEnabled}
                aria-invalid={errors.wordlimit ? 'true' : undefined}
                aria-describedby={errors.wordlimit ? `${id}-wordlimit-error` : undefined}
                onChange={(e) => set('wordlimit')(e.target.value)}
              />
              <label className="flex items-center gap-1.5">
                <input type="checkbox" checked={form.wordlimitEnabled} onChange={(e) => set('wordlimitEnabled')(e.target.checked)} />
                Enable
              </label>
            </div>
          </FormRow>
        )}
        {form.file && (
          <>
            <FormRow label="Maximum number of uploaded files" labelFor={`${id}-maxfiles`}>
              <select id={`${id}-maxfiles`} className="w-auto!" value={form.maxfiles} onChange={(e) => set('maxfiles')(e.target.value)}>
                {Array.from({ length: 20 }, (_, i) => String(i + 1)).map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </FormRow>
            <FormRow label="Maximum submission size" labelFor={`${id}-maxbytes`}>
              <select id={`${id}-maxbytes`} className="w-auto!" value={form.maxbytes} onChange={(e) => set('maxbytes')(e.target.value)}>
                {MAX_SIZES.map((bytes) => <option key={bytes} value={String(bytes)}>{bytes / MB} MB</option>)}
              </select>
            </FormRow>
          </>
        )}
      </FormSection>
      <FormSection id="grade" title="Grade">
        <FormRow label="Type" labelFor={`${id}-gradetype`}>
          <select id={`${id}-gradetype`} className="w-auto!" value="point" disabled>
            <option value="point">Point</option>
          </select>
        </FormRow>
        <FormRow label="Maximum grade" labelFor={`${id}-grade`} error={errors.grade} errorId={`${id}-grade-error`}>
          <input
            id={`${id}-grade`}
            type="number"
            min={1}
            max={MAX_GRADE}
            className="w-32!"
            value={form.grade}
            aria-invalid={errors.grade ? 'true' : undefined}
            aria-describedby={errors.grade ? `${id}-grade-error` : undefined}
            onChange={(e) => set('grade')(e.target.value)}
          />
        </FormRow>
      </FormSection>
    </ModForm>
  );
}

export function QuizModForm(props) {
  const id = useId();
  const state = useFormState({ name: '', intro: '', open: dateValue(0, false), close: dateValue(7, false) });
  const { form, set, errors } = state;
  const validate = (f) => ({
    name: f.name.trim() ? undefined : REQUIRED,
    close: f.open.enabled && f.close.enabled && toUnix(f.close) <= toUnix(f.open) ? 'The close date must be after the open date.' : undefined,
  });
  const toFields = (f) => ({ name: f.name.trim(), intro: plain(f.intro) ? f.intro : '', timeopen: toUnix(f.open), timeclose: toUnix(f.close) });

  return (
    <ModForm sections={['general', 'timing']} initiallyOpen={['general']} validate={validate} toFields={toFields} state={state} props={props}>
      <FormSection id="general" title="General">
        <NameField id={`${id}-name`} label="Name" value={form.name} onChange={set('name')} error={errors.name} />
        <EditorField id={`${id}-intro`} label="Description" value={form.intro} onChange={set('intro')} />
      </FormSection>
      <FormSection id="timing" title="Timing">
        <DateTimeSelector label="Open the quiz" value={form.open} onChange={set('open')} />
        <DateTimeSelector label="Close the quiz" value={form.close} onChange={set('close')} error={errors.close} />
      </FormSection>
    </ModForm>
  );
}

export function LabelModForm(props) {
  const id = useId();
  const state = useFormState({ name: '', text: '' });
  const { form, set, errors } = state;
  const validate = (f) => ({ text: plain(f.text) ? undefined : REQUIRED });
  // format 1 = FORMAT_HTML: isi berasal dari editor.
  const toFields = (f) => ({ name: f.name.trim(), text: f.text, format: 1 });

  return (
    <ModForm sections={['general']} initiallyOpen={['general']} validate={validate} toFields={toFields} state={state} props={props} withDisplay={false}>
      <FormSection id="general" title="General">
        <NameField id={`${id}-name`} label="Title in course index" required={false} value={form.name} onChange={set('name')} />
        <EditorField id={`${id}-text`} label="Text" required value={form.text} onChange={set('text')} error={errors.text} />
      </FormSection>
    </ModForm>
  );
}
