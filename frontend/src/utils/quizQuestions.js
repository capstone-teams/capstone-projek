// Soal pilihan ganda Quiz (dibuat manual di form aktivitas) dan batas isian generate AI.

export const AI_PROMPT_MAX = 2000;
export const MIN_OPTIONS = 2;
export const MAX_OPTIONS = 6;
export const MAX_AI_QUESTIONS = 30;
export const QUESTION_MODE = { MANUAL: 'manual', AI: 'ai' };
export const DIFFICULTY_LABELS = { mudah: 'Mudah', sedang: 'Sedang', sulit: 'Sulit' };

let uid = 0;
const nextKey = () => `q${(uid += 1)}`;

/** Soal pilihan ganda kosong: empat pilihan, belum ada kunci jawaban. */
export function newQuestion() {
  return { key: nextKey(), text: '', options: ['', '', '', ''], correct: null };
}

/** Pesan galat per soal (indeks → pesan); kosong bila semua soal valid. */
export function validateQuestions(questions) {
  const errors = {};
  questions.forEach((question, index) => {
    const filled = question.options.filter((option) => option.trim());
    if (!question.text.trim()) errors[index] = 'Pertanyaan wajib diisi.';
    else if (filled.length < MIN_OPTIONS) errors[index] = `Isi minimal ${MIN_OPTIONS} pilihan jawaban.`;
    else if (question.correct == null || !question.options[question.correct]?.trim()) errors[index] = 'Pilih kunci jawaban dari pilihan yang terisi.';
  });
  return errors;
}

/** Soal untuk disimpan: pilihan kosong dibuang dan kunci jawaban disesuaikan dengan urutan barunya. */
export function toQuestionFields(questions) {
  return questions.map((question) => {
    const kept = question.options.map((text, index) => ({ text: text.trim(), index })).filter((option) => option.text);
    const fields = { text: question.text.trim(), options: kept.map((option) => option.text), correct_index: kept.findIndex((option) => option.index === question.correct) };
    // Pembahasan dari AI ikut tersimpan sebagai umpan balik soal.
    return question.explanation?.trim() ? { ...fields, explanation: question.explanation.trim() } : fields;
  });
}

/** Soal hasil generate AI (question_text, options [{key, text}], correct_option_key) menjadi soal editor. */
export function fromGeneratedQuestions(questions = []) {
  return questions.map((question) => {
    const options = (question.options ?? []).map((option) => option.text ?? '');
    const correct = (question.options ?? []).findIndex((option) => option.key === question.correct_option_key);
    return { key: nextKey(), text: question.question_text ?? '', options, correct: correct >= 0 ? correct : null, explanation: question.explanation ?? '' };
  });
}
