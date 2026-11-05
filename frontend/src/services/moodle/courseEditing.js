/**
 * Edit mode kursus: sembunyikan, pindah, duplikat, hapus, ganti nama, dan tambah aktivitas.
 *
 * STATUS: belum lewat backend, karena API backend belum punya endpoint untuk mengubah isi kursus
 * (hanya GET /courses dan turunannya). Saat ini VITE_MOODLE_MOCK=true, jadi semua aksi hanya berjalan
 * di mockMoodle.js dan hilang saat halaman dimuat ulang. Saat endpoint tersedia, cukup ganti isi
 * fungsi di file ini; komponen dan useCourseEditing tidak perlu berubah.
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

// ---- Membuat aktivitas dari formulir aplikasi. Hanya mock; backend belum punya endpoint-nya.
// Rujukan dokumentasi Moodle: core tidak punya Web Service untuk membuat assign/label beserta isinya.
// mod_assign hanya punya fungsi PHP assign_add_instance(), bukan external function:
// https://phpdoc.moodledev.io/4.4/d3/d4f/group__mod__assign.html

export const CAN_CREATE_IN_APP = false;

/**
 * fields Assignment: { name, intro, allowsubmissionsfromdate, duedate, cutoffdate, grade }
 *   (tanggal = Unix detik, 0 = tanpa tanggal)
 *   + jenis pengumpulan { onlinetext_enabled, onlinetext_wordlimit, file_enabled, file_maxfiles, file_maxbytes }.
 * fields Quiz: { name, intro, timeopen, timeclose }.
 * fields Text and media area: { name, text, format } (format 1 = HTML dari editor).
 */
export async function createActivity(courseId, sectionNumber, modname, fields) {
  if (!CAN_CREATE_IN_APP) {
    throw new MoodleError('notsupported', 'Pembuatan aktivitas belum tersedia di API backend.');
  }
  return callWs('mock_course_create_activity', { courseid: courseId, sectionnum: sectionNumber, modname, ...fields });
}
