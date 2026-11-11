import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../src/services/apiClient';
import { activityRequestBody, createActivity, generateActivity } from '../src/services/moodle/courseEditing';

// Tambah aktivitas dari halaman kursus lewat Backend Gateway (plugin local_capstonebridge di backend).
describe('aktivitas kursus lewat Backend Gateway', () => {
  afterEach(() => vi.restoreAllMocks());

  it('Assignment: tanggal, nilai, dan jenis pengumpulan dipetakan ke body API', () => {
    expect(activityRequestBody(3, 'assign', {
      name: 'Tugas ERD',
      intro: '<p>Buat ERD.</p>',
      duedate: 200,
      grade: 80,
      onlinetext_enabled: 1,
      file_enabled: 0,
      file_maxfiles: 5,
    })).toEqual({
      section: 3,
      modname: 'assign',
      name: 'Tugas ERD',
      intro: '<p>Buat ERD.</p>',
      duedate: 200,
      grade: 80,
      onlinetext_enabled: true,
      file_enabled: false,
      file_maxfiles: 5,
    });
  });

  it('Quiz: kunci jawaban menjadi answers.correct dan pembahasan menjadi generalfeedback', () => {
    const body = activityRequestBody(2, 'quiz', {
      name: 'Kuis SQL',
      intro: '',
      timelimit_minutes: 15,
      attempts: 2,
      questions: [{ text: 'Perintah membaca data?', options: ['INSERT', 'SELECT'], correct_index: 1, explanation: 'SELECT membaca data.' }],
    });
    expect(body).toMatchObject({ timelimit_minutes: 15, attempts: 2 });
    expect(body.questions).toEqual([{
      text: 'Perintah membaca data?',
      generalfeedback: 'SELECT membaca data.',
      answers: [{ text: 'INSERT', correct: false }, { text: 'SELECT', correct: true }],
    }]);
  });

  it('membuat aktivitas dengan POST /integrations/moodle/courses/{id}/activities', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({ cmid: 91, modname: 'label', section: 1, created: true });
    await expect(createActivity(48, 1, 'label', { name: '', text: '<p>Halo</p>', format: 1 })).resolves.toMatchObject({ cmid: 91 });
    expect(post).toHaveBeenCalledWith('/integrations/moodle/courses/48/activities', { section: 1, modname: 'label', name: '', text: '<p>Halo</p>' });
  });

  it('kursus project backend (bukan ID Moodle) ditolak sebelum memanggil API', async () => {
    const post = vi.spyOn(api, 'post');
    await expect(createActivity('5AH7inFLxJDRKEa34saR9c', 1, 'label', { text: '<p>x</p>' })).rejects.toThrow('kursus Moodle');
    expect(post).not.toHaveBeenCalled();
  });

  it('generate mengirim referensi dan file sebagai multipart', async () => {
    const upload = vi.spyOn(api, 'upload').mockResolvedValue({ name: 'Kuis', questions: [] });
    const file = new File(['isi'], 'slide.pdf', { type: 'application/pdf' });
    await generateActivity(48, { modname: 'quiz', section: 4, aiPrompt: 'Fokus JOIN', aiQuestionCount: 5, aiDifficulty: 'sulit', useWeek: true, useRps: false, file });
    const [path, form] = upload.mock.calls[0];
    expect(path).toBe('/integrations/moodle/courses/48/activities/generate');
    expect(Object.fromEntries([...form.entries()].map(([key, value]) => [key, value instanceof File ? value.name : value]))).toEqual({
      modname: 'quiz',
      section: '4',
      instruction: 'Fokus JOIN',
      question_count: '5',
      difficulty: 'sulit',
      use_week: 'true',
      use_rps: 'false',
      reference_file: 'slide.pdf',
    });
  });
});
