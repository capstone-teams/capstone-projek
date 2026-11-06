import PendingFeatureNote from '../../ai/PendingFeatureNote';
import { FormRow, FormSection } from './MoodleForm';
import { AI_PROMPT_MAX, DIFFICULTY_LABELS, MAX_AI_QUESTIONS, MAX_OPTIONS, MIN_OPTIONS, QUESTION_MODE, newQuestion } from '../../../utils/quizQuestions';

/*
 * Bagian tambahan form aktivitas (bukan bagian modedit.php Moodle): generate isi aktivitas dengan AI dan editor
 * soal pilihan ganda untuk Quiz. Backend belum punya endpoint generate konten aktivitas, jadi tombol generate
 * tampil nonaktif sampai halaman memberi `onGenerate`.
 */

function GenerateButton({ label, onGenerate, generating, pendingText }) {
  return (
    <div>
      <button type="button" className="btn btn--secondary" disabled={!onGenerate || generating} onClick={onGenerate}>
        {generating ? 'Membuat…' : label}
      </button>
      {!onGenerate && <PendingFeatureNote>{pendingText}</PendingFeatureNote>}
    </div>
  );
}

function PromptField({ id, value, onChange, placeholder }) {
  return (
    <FormRow label="Prompt tambahan" labelFor={`${id}-ai`}>
      <textarea
        id={`${id}-ai`}
        rows={4}
        maxLength={AI_PROMPT_MAX}
        value={value}
        placeholder={placeholder}
        aria-describedby={`${id}-ai-hint`}
        onChange={(event) => onChange(event.target.value)}
      />
      <p id={`${id}-ai-hint`} className="mt-1 text-sm text-muted">
        Opsional. Instruksi untuk agent AI saat membuat isi aktivitas ini.
        <span className="ml-2 whitespace-nowrap">{value.length}/{AI_PROMPT_MAX}</span>
      </p>
    </FormRow>
  );
}

/** "Generate otomatis (AI)": prompt tambahan dan tombol generate isi aktivitas. */
export function AiGenerateSection({ id, value, onChange, placeholder, onGenerate, generating }) {
  return (
    <FormSection id="ai" title="Generate otomatis (AI)">
      <PromptField id={id} value={value} onChange={onChange} placeholder={placeholder} />
      <FormRow label="" labelId={`${id}-ai-action`}>
        <GenerateButton label="Generate dengan AI" onGenerate={onGenerate} generating={generating} pendingText="Generate isi aktivitas dengan AI belum tersedia." />
      </FormRow>
    </FormSection>
  );
}

function QuestionEditor({ id, index, question, error, onChange, onRemove }) {
  const set = (patch) => onChange({ ...question, ...patch });
  const setOption = (optionIndex, text) => set({ options: question.options.map((option, i) => (i === optionIndex ? text : option)) });
  const removeOption = (optionIndex) => {
    const options = question.options.filter((_, i) => i !== optionIndex);
    const correct = question.correct === optionIndex ? null : question.correct > optionIndex ? question.correct - 1 : question.correct;
    set({ options, correct });
  };
  const base = `${id}-q${question.key}`;
  return (
    <fieldset className="rounded-lg border border-line p-3" aria-labelledby={`${base}-legend`} data-question={index + 1}>
      <legend id={`${base}-legend`} className="px-1 text-sm font-semibold">Soal {index + 1}</legend>
      <label htmlFor={`${base}-text`} className="mb-1 block text-sm">Pertanyaan</label>
      <textarea
        id={`${base}-text`}
        rows={2}
        value={question.text}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={error ? `${base}-error` : undefined}
        className={error ? 'border-danger' : undefined}
        onChange={(event) => set({ text: event.target.value })}
      />
      <div role="radiogroup" aria-label={`Pilihan jawaban soal ${index + 1}`} className="mt-3 flex flex-col gap-2">
        {question.options.map((option, optionIndex) => (
          <div key={optionIndex} className="flex items-center gap-2">
            <input
              type="radio"
              name={`${base}-correct`}
              checked={question.correct === optionIndex}
              aria-label={`Jadikan pilihan ${String.fromCharCode(65 + optionIndex)} kunci jawaban`}
              onChange={() => set({ correct: optionIndex })}
            />
            <span className="w-5 text-sm font-semibold" aria-hidden="true">{String.fromCharCode(65 + optionIndex)}</span>
            <input
              className="min-w-0 flex-1"
              value={option}
              aria-label={`Pilihan ${String.fromCharCode(65 + optionIndex)} soal ${index + 1}`}
              onChange={(event) => setOption(optionIndex, event.target.value)}
            />
            <button type="button" className="btn btn--ghost btn--sm" disabled={question.options.length <= MIN_OPTIONS} aria-label={`Hapus pilihan ${String.fromCharCode(65 + optionIndex)} soal ${index + 1}`} onClick={() => removeOption(optionIndex)}>
              ✕
            </button>
          </div>
        ))}
      </div>
      {error && <p id={`${base}-error`} className="mt-2 text-sm text-danger">{error}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" className="btn btn--ghost btn--sm" disabled={question.options.length >= MAX_OPTIONS} onClick={() => set({ options: [...question.options, ''] })}>
          + Pilihan
        </button>
        <button type="button" className="btn btn--ghost btn--sm text-danger" onClick={onRemove}>Hapus soal</button>
      </div>
    </fieldset>
  );
}

/**
 * Bagian "Soal" Quiz: buat soal pilihan ganda secara manual, atau minta AI membuatnya (prompt, jumlah, tingkat
 * kesulitan). value = { mode, questions, aiPrompt, aiCount, aiDifficulty }.
 */
export function QuizQuestionsSection({ id, value, onChange, errors = {}, onGenerate, generating }) {
  const set = (patch) => onChange({ ...value, ...patch });
  const updateQuestion = (index, question) => set({ questions: value.questions.map((q, i) => (i === index ? question : q)) });
  return (
    <FormSection id="questions" title="Soal">
      <FormRow label="Cara membuat soal" labelId={`${id}-mode`}>
        <div role="radiogroup" aria-labelledby={`${id}-mode`} className="flex flex-wrap gap-x-6 gap-y-2 md:pt-2">
          <label className="flex items-center gap-1.5">
            <input type="radio" name={`${id}-mode`} checked={value.mode === QUESTION_MODE.MANUAL} onChange={() => set({ mode: QUESTION_MODE.MANUAL })} />
            Buat manual
          </label>
          <label className="flex items-center gap-1.5">
            <input type="radio" name={`${id}-mode`} checked={value.mode === QUESTION_MODE.AI} onChange={() => set({ mode: QUESTION_MODE.AI })} />
            Generate otomatis (AI)
          </label>
        </div>
      </FormRow>

      {value.mode === QUESTION_MODE.MANUAL ? (
        <FormRow label="Soal pilihan ganda" labelId={`${id}-questions`}>
          <div className="flex flex-col gap-3" aria-labelledby={`${id}-questions`}>
            {value.questions.length === 0 && <p className="text-sm text-muted">Belum ada soal. Quiz tetap dapat disimpan dan soal ditambahkan nanti.</p>}
            {value.questions.map((question, index) => (
              <QuestionEditor
                key={question.key}
                id={id}
                index={index}
                question={question}
                error={errors[index]}
                onChange={(next) => updateQuestion(index, next)}
                onRemove={() => set({ questions: value.questions.filter((_, i) => i !== index) })}
              />
            ))}
            <button type="button" className="btn btn--ghost self-start" onClick={() => set({ questions: [...value.questions, newQuestion()] })}>
              + Tambah soal
            </button>
          </div>
        </FormRow>
      ) : (
        <>
          <PromptField id={`${id}-quiz`} value={value.aiPrompt} onChange={(aiPrompt) => set({ aiPrompt })} placeholder="Mis. Soal tentang SQL JOIN dan normalisasi untuk mahasiswa semester 3." />
          <FormRow label="Jumlah soal" labelFor={`${id}-count`}>
            <input id={`${id}-count`} type="number" min={1} max={MAX_AI_QUESTIONS} className="w-32!" value={value.aiCount} onChange={(event) => set({ aiCount: event.target.value })} />
          </FormRow>
          <FormRow label="Tingkat kesulitan" labelFor={`${id}-difficulty`}>
            <select id={`${id}-difficulty`} className="w-auto!" value={value.aiDifficulty} onChange={(event) => set({ aiDifficulty: event.target.value })}>
              {Object.entries(DIFFICULTY_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
          </FormRow>
          <FormRow label="" labelId={`${id}-quiz-action`}>
            <GenerateButton label="Generate soal dengan AI" onGenerate={onGenerate} generating={generating} pendingText="Generate soal quiz dengan AI belum tersedia." />
          </FormRow>
        </>
      )}
    </FormSection>
  );
}
