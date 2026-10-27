/**
 * Edit mode kursus: fungsi yang dipakai editor kursus Moodle 4.x/5.x.
 *
 * - core_courseformat_update_course: aksi pada aktivitas/section (course/format/classes/stateactions.php).
 * - core_update_inplace_editable: ubah nama aktivitas/section (ikon pensil).
 *
 * Keduanya bertanda 'ajax' => true di lib/db/services.php dan TIDAK termasuk layanan
 * moodle_mobile_app; pada Moodle nyata tambahkan ke external service yang dipakai frontend.
 *
 * (moodledev.io):
 * - Fungsi editor kursus pengganti core_course_edit_section/edit_module sejak 4.0:
 *   https://moodledev.io/docs/4.4/apis/plugintypes/format/migration
 * - Cara fungsi dibuka ke 'ajax' dan layanan mobile (MOODLE_OFFICIAL_MOBILE_SERVICE):
 *   https://moodledev.io/docs/5.1/apis/subsystems/external/description
 * - Service kustom untuk fungsi di luar layanan bawaan:
 *   https://moodledev.io/docs/5.0/apis/subsystems/external/advanced/custom-services
 */
import { USE_MOODLE_MOCK } from '../config';
import { MoodleError, callWs, moodleUrl } from './moodleClient';

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

// ---- Membuat aktivitas dari formulir aplikasi.
// Moodle core belum menyediakan Web Service untuk membuat assign/label beserta isinya
// (core_courseformat_create_module hanya untuk modul FEATURE_QUICKCREATE, yaitu mod_subsection).
// Di dokumentasi mod_assign hanya ada fungsi PHP assign_add_instance(), bukan external function:
// https://phpdoc.moodledev.io/4.4/d3/d4f/group__mod__assign.html
// Fungsi baru perlu ditulis sendiri (plugin Moodle), pola penulisannya:
// https://moodledev.io/docs/5.0/apis/subsystems/external/writing-a-service
// Sampai tim memilih jalurnya (plugin Moodle atau endpoint backend), hanya mock yang mendukung.

export const CAN_CREATE_IN_APP = USE_MOODLE_MOCK;

/**
 * fields Assignment: { name, intro, allowsubmissionsfromdate, duedate, grade } (tanggal = Unix detik, 0 = tanpa tanggal).
 * fields Quiz: { name, intro, timeopen, timeclose }.
 * fields Text and media area: { text }.
 */
export async function createActivity(courseId, sectionNumber, modname, fields) {
  if (!CAN_CREATE_IN_APP) {
    throw new MoodleError('notsupported', 'Moodle belum menyediakan layanan untuk membuat aktivitas dari aplikasi. Gunakan formulir Moodle.');
  }
  return callWs('mock_course_create_activity', { courseid: courseId, sectionnum: sectionNumber, modname, ...fields });
}

// ---- Halaman Moodle untuk aksi yang memerlukan formulir lengkap (dibuka di tab baru).

export const moodleEditUrl = {
  activitySettings: (cmId) => moodleUrl(`/course/modedit.php?update=${cmId}`),
  assignRoles: (contextId) => moodleUrl(`/admin/roles/assign.php?contextid=${contextId}`),
  sectionSettings: (sectionId) => moodleUrl(`/course/editsection.php?id=${sectionId}`),
  addActivity: (courseId, sectionNumber, modname) => moodleUrl(`/course/modedit.php?add=${modname}&course=${courseId}&section=${sectionNumber}&return=0`),
};
