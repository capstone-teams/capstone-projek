/**
 * Edit mode kursus: sembunyikan, pindah, duplikat, hapus, ganti nama, dan tambah aktivitas.
 *
 * STATUS: tambah aktivitas (Assignment, Quiz, Text and media area) dan draf AI-nya sudah lewat Backend Gateway
 * (lihat bagian bawah file). Aksi editor lain (sembunyikan, pindah, duplikat, hapus, ganti nama) belum punya
 * endpoint backend dan masih memanggil Web Service Moodle langsung (hanya aktif bila VITE_MOODLE_URL diatur).
 * Saat endpoint tersedia, cukup ganti isi fungsi di file ini; komponen dan useCourseEditing tidak perlu berubah.
 *
 * Rujukan dokumentasi Moodle (nama aksi dan fungsi di bawah mengikuti editor kursus Moodle 4.x/5.x):
 * - core_courseformat_update_course menggantikan core_course_edit_section/edit_module sejak 4.0:
 *   https://moodledev.io/docs/4.4/apis/plugintypes/format/migration
 * - Fungsi ini dan core_update_inplace_editable hanya 'ajax', tidak termasuk layanan mobile:
 *   https://moodledev.io/docs/5.1/apis/subsystems/external/description
 * - Service kustom untuk fungsi di luar layanan bawaan:
 *   https://moodledev.io/docs/5.0/apis/subsystems/external/advanced/custom-services
 */
import { MoodleError, callWs } from './moodleClient';
import { api } from '../apiClient';
import { isMoodleCourseId } from '../../utils/courseId';

/** Aksi aktivitas (course module) yang dikirim ke core_courseformat_update_course. */
export const CM_ACTION = {
  HIDE: 'cm_hide',
  SHOW: 'cm_show',
  DUPLICATE: 'cm_duplicate',
  DELETE: 'cm_delete',
  MOVE: 'cm_move',
  INDENT: 'cm_moveright',
  OUTDENT: 'cm_moveleft',
};

export const SECTION_ACTION = {
  HIDE: 'section_hide',
  SHOW: 'section_show',
  ADD: 'section_add',
};

/** Jalankan satu aksi editor; respons (state JSON) diabaikan karena isi kursus dimuat ulang. */
export function updateCourseState(courseId, action, ids = [], { targetSectionId, targetCmId } = {}) {
  return callWs('core_courseformat_update_course', {
    action,
    courseid: courseId,
    ids,
    targetsectionid: targetSectionId,
    targetcmid: targetCmId,
  });
}

/** targetCmId: sisipkan sebelum aktivitas tersebut; tanpa targetCmId: ke akhir section. */
export function moveActivity(courseId, cmId, targetSectionId, targetCmId) {
  return updateCourseState(courseId, CM_ACTION.MOVE, [cmId], { targetSectionId, targetCmId });
}

export function renameActivity(cmId, name) {
  return callWs('core_update_inplace_editable', { component: 'core_course', itemtype: 'activityname', itemid: cmId, value: name });
}

/** Nama section ditangani plugin format kursus (format_topics, format_weeks, ...). */
export function renameSection(courseFormat, sectionId, name) {
  return callWs('core_update_inplace_editable', {
    component: `format_${courseFormat || 'topics'}`,
    itemtype: 'sectionname',
    itemid: sectionId,
    value: name,
  });
}

// ---- Membuat aktivitas dari formulir aplikasi lewat Backend Gateway.
// Rujukan dokumentasi Moodle: core tidak punya Web Service untuk membuat assign/quiz/label beserta isinya, jadi
// backend memakai function plugin local_capstonebridge yang sudah terpasang untuk eksekusi Moodle (create_assign,
// create_quiz, create_page). Text and media area disimpan sebagai Page dan isinya tampil di kartu minggu:
// POST /integrations/moodle/courses/{id}/activities dan .../activities/generate (draf AI).

export const CAN_CREATE_IN_APP = true;

const activitiesPath = (courseId) => {
  if (!isMoodleCourseId(courseId)) {
    throw new MoodleError('notsupported', 'Aktivitas hanya dapat ditambahkan pada kursus Moodle.');
  }
  return `/integrations/moodle/courses/${courseId}/activities`;
};

/** Isian formulir menjadi body POST .../activities sesuai jenis aktivitas. */
export function activityRequestBody(sectionNumber, modname, fields) {
  const base = { section: sectionNumber, modname };
  if (modname === 'assign') {
    return {
      ...base,
      name: fields.name,
      intro: fields.intro ?? '',
      duedate: fields.duedate || 0,
      grade: fields.grade,
      onlinetext_enabled: Boolean(fields.onlinetext_enabled),
      file_enabled: Boolean(fields.file_enabled),
      file_maxfiles: fields.file_maxfiles || 1,
    };
  }
  if (modname === 'quiz') {
    return {
      ...base,
      name: fields.name,
      intro: fields.intro ?? '',
      timelimit_minutes: fields.timelimit_minutes || 0,
      attempts: fields.attempts ?? 1,
      questions: (fields.questions ?? []).map((question) => ({
        text: question.text,
        generalfeedback: question.explanation ?? '',
        answers: question.options.map((text, index) => ({ text, correct: index === question.correct_index })),
      })),
    };
  }
  return { ...base, name: fields.name ?? '', text: fields.text };
}

/**
 * fields Assignment: { name, intro, duedate (Unix detik, 0 = tanpa), grade }
 *   + jenis pengumpulan { onlinetext_enabled, file_enabled, file_maxfiles }.
 * fields Quiz: { name, intro, timelimit_minutes, attempts, questions: [{ text, options, correct_index, explanation? }] }.
 * fields Text and media area: { name, text, format } (format 1 = HTML dari editor).
 * Mengembalikan { cmid, modname, section, created }.
 */
export async function createActivity(courseId, sectionNumber, modname, fields) {
  return api.post(activitiesPath(courseId), activityRequestBody(sectionNumber, modname, fields));
}

/**
 * Draf isi aktivitas dari AI (tidak membuat apa pun di Moodle). request:
 * { modname, section, aiPrompt, aiQuestionCount?, aiDifficulty?, useWeek, useRps, file? }.
 * Mengembalikan { name, intro, text, questions, references_used }.
 */
export async function generateActivity(courseId, request) {
  const form = new FormData();
  form.append('modname', request.modname);
  form.append('section', String(request.section));
  form.append('instruction', request.aiPrompt ?? '');
  if (request.aiQuestionCount) form.append('question_count', String(request.aiQuestionCount));
  if (request.aiDifficulty) form.append('difficulty', request.aiDifficulty);
  form.append('use_week', request.useWeek === false ? 'false' : 'true');
  form.append('use_rps', request.useRps === false ? 'false' : 'true');
  if (request.file) form.append('reference_file', request.file, request.file.name);
  return api.upload(`${activitiesPath(courseId)}/generate`, form);
}
