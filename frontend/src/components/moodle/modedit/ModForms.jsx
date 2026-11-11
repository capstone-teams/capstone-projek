import { useId, useState } from 'react';
import { ErrorAlert } from '../../ui';
import MoodleEditor from '../submission/MoodleEditor';
import { DateTimeSelector, FormRow, FormSection, FormSections } from './MoodleForm';
import { dateValue, toUnix } from '../../../utils/dateSelector';
import { AiGenerateSection, QuizQuestionsSection } from './AiGenerate';
import { QUESTION_MODE, fromGeneratedQuestions, toQuestionFields, validateQuestions } from '../../../utils/quizQuestions';

/*
 * Formulir "New <aktivitas>" seperti course/modedit.php: field, bagian, default, dan pesan validasi
 * diambil dari mod/assign, mod/quiz, dan mod/label (mod_form.php dan lang/en). Hanya setelan yang
 * benar-benar disimpan yang ditampilkan.
 */

const REQUIRED = 'You must supply a value here.';
const MAX_GRADE = 100;
const plain = (html) => new DOMParser().parseFromString(html, 'text/html').body.textContent.trim();

function useFormState(initial) {
  const [form, setForm] = useState(initial);
  const [errors, setErrors] = useState({});
  const set = (key) => (value) => {
    setForm((current) => ({ ...current, [key]: value }));
    if (errors[key]) setErrors((current) => ({ ...current, [key]: undefined }));
  };
  return { form, set, setForm, errors, setErrors };
}

/**
 * Draf AI untuk form: `onGenerate(request)` dari halaman mengembalikan draf ({ name, intro, text, questions,
 * references_used }) yang diterapkan `apply`. Referensi (materi minggu, RPS, file) dipilih di form.
 */
function useAiDraft(onGenerate) {
  const [status, setStatus] = useState({ generating: false, error: null, used: null });
  const [references, setReferences] = useState({ useWeek: true, useRps: true, file: null });
  const run = onGenerate
    ? async (request, apply) => {
      setStatus({ generating: true, error: null, used: null });
      try {
        const draft = await onGenerate({ ...request, ...references });
        if (draft) apply(draft);
        setStatus({ generating: false, error: null, used: draft ? draft.references_used ?? [] : null });
      } catch (error) {
        setStatus({ generating: false, error, used: null });
      }
    }
    : undefined;
  return { status, references, setReferences, run };
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
  // Editor membaca isi awal saat dipasang; pemanggil mengganti `key` agar draf AI tampil di editor.
  return (
    <FormRow label={label} labelId={`${id}-label`} required={required} error={error} errorId={`${id}-error`}>
      <MoodleEditor id={id} labelId={`${id}-label`} initialValue={value} onChange={onChange} invalid={!!error} describedBy={error ? `${id}-error` : undefined} />
    </FormRow>
  );
}

/** Tombol bawah form: satu tombol simpan (kembali ke kursus) dan batal; tanpa API pembuatan, simpan dinonaktifkan. */
function ModFormButtons({ canCreate, pending, onCancel }) {
  return (
    <div className="mt-6 grid gap-x-6 md:grid-cols-[minmax(0,1fr)_minmax(0,3fr)]">
      <div className="flex flex-wrap gap-2 md:col-start-2">
        <button type="submit" className="btn btn--primary" disabled={pending || !canCreate}>Save and return to course</button>
        <button type="button" className="btn btn--secondary" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

// Data generate AI untuk halaman (argumen kedua onSubmit), terpisah dari isian aktivitas.
const aiOptions = (form) => ({ aiPrompt: form.aiPrompt.trim() });

function ModForm({ sections, initiallyOpen, validate, toFields, state, props, extras = aiOptions, children }) {
  const submit = (event) => {
    event.preventDefault();
    const found = validate(state.form);
    state.setErrors(found);
    if (Object.values(found).some(Boolean)) {
      // Rujukan perilaku formulir Moodle: buka bagian yang berisi error lalu fokus ke field pertama yang salah.
      const form = event.currentTarget;
      setTimeout(() => {
        const field = form.querySelector('[aria-invalid="true"], [data-invalid="true"]');
        const body = field?.closest('[hidden]');
        if (body) form.querySelector(`[aria-controls="${body.id}"]`)?.click();
        setTimeout(() => (field?.matches('input, select, textarea, [contenteditable]') ? field : field?.querySelector('select, input'))?.focus());
      });
      return;
    }
    props.onSubmit(toFields(state.form), extras(state.form));
  };
  return (
    <form onSubmit={submit} noValidate>
      <ErrorAlert error={props.error} />
      {!props.canCreate && (
        <p className="mb-3 text-sm text-muted">Menyimpan aktivitas baru belum tersedia; isian formulir belum dapat disimpan.</p>
      )}
      <FormSections ids={sections} initiallyOpen={initiallyOpen}>{children}</FormSections>
      <ModFormButtons canCreate={props.canCreate} pending={props.pending} onCancel={props.onCancel} />
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
    due: dateValue(7, true),
    onlinetext: false,
    file: true, maxfiles: '1',
    grade: '100',
    aiPrompt: '',
  });
  const { form, set, setForm, errors } = state;
  const ai = useAiDraft(props.onGenerate);
  const [editorKey, setEditorKey] = useState(0);
  const generate = ai.run && (() => ai.run({ aiPrompt: form.aiPrompt.trim() }, (draft) => {
    setForm((current) => ({ ...current, name: current.name.trim() ? current.name : draft.name ?? '', intro: draft.intro ?? current.intro }));
    setEditorKey((key) => key + 1);
  }));
  const validate = (f) => {
    const found = {};
    if (!f.name.trim()) found.name = REQUIRED;
    if (!f.onlinetext && !f.file) found.types = 'Select at least one submission type.';
    const grade = Number(f.grade);
    if (!Number.isInteger(grade) || grade < 1 || grade > MAX_GRADE) found.grade = `Invalid grade value. This must be an integer between 1 and ${MAX_GRADE}`;
    return found;
  };
  const toFields = (f) => ({
    name: f.name.trim(),
    intro: plain(f.intro) ? f.intro : '',
    duedate: toUnix(f.due),
    grade: Number(f.grade),
    // Nama setelan mengikuti plugin assignsubmission_onlinetext dan assignsubmission_file.
    onlinetext_enabled: f.onlinetext ? 1 : 0,
    file_enabled: f.file ? 1 : 0,
    file_maxfiles: Number(f.maxfiles),
  });

  return (
    <ModForm sections={['general', 'availability', 'submissiontypes', 'grade', 'ai']} initiallyOpen={['general', 'availability', 'submissiontypes', 'ai']}
      validate={validate} toFields={toFields} state={state} props={props}
    >
      <FormSection id="general" title="General">
        <NameField id={`${id}-name`} label="Assignment name" value={form.name} onChange={set('name')} error={errors.name} />
        <EditorField key={editorKey} id={`${id}-intro`} label="Description" value={form.intro} onChange={set('intro')} />
      </FormSection>
      <FormSection id="availability" title="Availability">
        <DateTimeSelector label="Due date" value={form.due} onChange={set('due')} error={errors.due} />
      </FormSection>
      <FormSection id="submissiontypes" title="Submission types">
        <FormRow label="Submission types" labelId={`${id}-types`} error={errors.types} errorId={`${id}-types-error`}>
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
        {form.file && (
          <FormRow label="Maximum number of uploaded files" labelFor={`${id}-maxfiles`}>
            <select id={`${id}-maxfiles`} className="w-auto!" value={form.maxfiles} onChange={(e) => set('maxfiles')(e.target.value)}>
              {Array.from({ length: 20 }, (_, i) => String(i + 1)).map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </FormRow>
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
      <AiGenerateSection
        id={id}
        value={form.aiPrompt}
        onChange={set('aiPrompt')}
        onGenerate={generate}
        generating={ai.status.generating}
        status={ai.status}
        references={props.onGenerate ? ai.references : null}
        onReferencesChange={ai.setReferences}
        placeholder="Mis. Buat tugas studi kasus tentang normalisasi basis data dengan tiga pertanyaan dan rubrik penilaian."
      />
    </ModForm>
  );
}

export function QuizModForm(props) {
  const id = useId();
  const state = useFormState({
    name: '', intro: '', timelimit: '', attempts: '1',
    quiz: { mode: QUESTION_MODE.MANUAL, questions: [], aiPrompt: '', aiCount: '10', aiDifficulty: 'sedang' },
  });
  const { form, set, setForm, errors, setErrors } = state;
  const ai = useAiDraft(props.onGenerate);
  const [editorKey, setEditorKey] = useState(0);
  const manual = (f) => f.quiz.mode === QUESTION_MODE.MANUAL;
  // Soal hasil AI masuk ke editor manual agar dapat diperiksa dan disunting sebelum disimpan.
  const generate = ai.run && (() => ai.run(
    { aiPrompt: form.quiz.aiPrompt.trim(), aiQuestionCount: Number(form.quiz.aiCount) || 10, aiDifficulty: form.quiz.aiDifficulty },
    (draft) => {
      setForm((current) => ({
        ...current,
        name: current.name.trim() ? current.name : draft.name ?? '',
        intro: draft.intro || current.intro,
        quiz: { ...current.quiz, mode: QUESTION_MODE.MANUAL, questions: [...current.quiz.questions, ...fromGeneratedQuestions(draft.questions)] },
      }));
      setEditorKey((key) => key + 1);
      setErrors((current) => ({ ...current, questionErrors: undefined, questionsMissing: undefined }));
    },
  ));
  const validate = (f) => {
    const questionErrors = manual(f) ? validateQuestions(f.quiz.questions) : {};
    return {
      name: f.name.trim() ? undefined : REQUIRED,
      timelimit: f.timelimit === '' || (Number.isInteger(Number(f.timelimit)) && Number(f.timelimit) >= 1) ? undefined : 'You must enter a number here.',
      questionErrors: Object.keys(questionErrors).length ? questionErrors : undefined,
      // Quiz di Moodle dibuat beserta soalnya (plugin local_capstonebridge), jadi minimal satu soal.
      questionsMissing: manual(f) && f.quiz.questions.length ? undefined : 'Quiz wajib memiliki minimal satu soal. Tambahkan soal atau generate dengan AI.',
    };
  };
  // Soal manual ikut tersimpan bersama quiz; mode AI menunggu hasil generate.
  const toFields = (f) => ({
    name: f.name.trim(), intro: plain(f.intro) ? f.intro : '',
    timelimit_minutes: f.timelimit === '' ? 0 : Number(f.timelimit), attempts: Number(f.attempts),
    questions: manual(f) ? toQuestionFields(f.quiz.questions) : [],
  });
  const extras = (f) => ({ aiPrompt: f.quiz.aiPrompt.trim(), aiQuestionCount: Number(f.quiz.aiCount) || null, aiDifficulty: f.quiz.aiDifficulty });
  const setQuiz = (quiz) => {
    set('quiz')(quiz);
    if (errors.questionErrors || errors.questionsMissing) setErrors((current) => ({ ...current, questionErrors: undefined, questionsMissing: undefined }));
  };

  return (
    <ModForm sections={['general', 'timing', 'questions']} initiallyOpen={['general', 'questions']} validate={validate} toFields={toFields} extras={extras} state={state} props={props}>
      <FormSection id="general" title="General">
        <NameField id={`${id}-name`} label="Name" value={form.name} onChange={set('name')} error={errors.name} />
        <EditorField key={editorKey} id={`${id}-intro`} label="Description" value={form.intro} onChange={set('intro')} />
      </FormSection>
      <FormSection id="timing" title="Timing">
        <FormRow label="Time limit (minutes)" labelFor={`${id}-timelimit`} error={errors.timelimit} errorId={`${id}-timelimit-error`}>
          <input
            id={`${id}-timelimit`}
            type="number"
            min={1}
            className="w-32!"
            placeholder="Tanpa batas"
            value={form.timelimit}
            aria-invalid={errors.timelimit ? 'true' : undefined}
            aria-describedby={errors.timelimit ? `${id}-timelimit-error` : undefined}
            onChange={(e) => set('timelimit')(e.target.value)}
          />
        </FormRow>
        <FormRow label="Attempts allowed" labelFor={`${id}-attempts`}>
          <select id={`${id}-attempts`} className="w-auto!" value={form.attempts} onChange={(e) => set('attempts')(e.target.value)}>
            <option value="0">Unlimited</option>
            {Array.from({ length: 10 }, (_, i) => String(i + 1)).map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </FormRow>
      </FormSection>
      <QuizQuestionsSection
        id={id}
        value={form.quiz}
        onChange={setQuiz}
        errors={errors.questionErrors}
        missingError={errors.questionsMissing}
        onGenerate={generate}
        generating={ai.status.generating}
        status={ai.status}
        references={props.onGenerate ? ai.references : null}
        onReferencesChange={ai.setReferences}
      />
    </ModForm>
  );
}

export function LabelModForm(props) {
  const id = useId();
  const state = useFormState({ name: '', text: '', aiPrompt: '' });
  const { form, set, setForm, errors } = state;
  const ai = useAiDraft(props.onGenerate);
  const [editorKey, setEditorKey] = useState(0);
  const generate = ai.run && (() => ai.run({ aiPrompt: form.aiPrompt.trim() }, (draft) => {
    setForm((current) => ({ ...current, name: current.name.trim() ? current.name : draft.name ?? '', text: draft.text ?? current.text }));
    setEditorKey((key) => key + 1);
  }));
  const validate = (f) => ({ text: plain(f.text) ? undefined : REQUIRED });
  // format 1 = FORMAT_HTML: isi berasal dari editor.
  const toFields = (f) => ({ name: f.name.trim(), text: f.text, format: 1 });

  return (
    <ModForm sections={['general', 'ai']} initiallyOpen={['general', 'ai']} validate={validate} toFields={toFields} state={state} props={props}>
      <FormSection id="general" title="General">
        <NameField id={`${id}-name`} label="Title in course index" required={false} value={form.name} onChange={set('name')} />
        <EditorField key={editorKey} id={`${id}-text`} label="Text" required value={form.text} onChange={set('text')} error={errors.text} />
      </FormSection>
      <AiGenerateSection
        id={id}
        value={form.aiPrompt}
        onChange={set('aiPrompt')}
        onGenerate={generate}
        generating={ai.status.generating}
        status={ai.status}
        references={props.onGenerate ? ai.references : null}
        onReferencesChange={ai.setReferences}
        placeholder="Mis. Tulis ringkasan materi minggu ini dalam tiga paragraf untuk mahasiswa semester tiga."
      />
    </ModForm>
  );
}
