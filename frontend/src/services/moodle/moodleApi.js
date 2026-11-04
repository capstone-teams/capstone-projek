/**
 * Data kursus yang belum punya API backend: kursus, peserta, nilai, aktivitas, dan pengumpulan tugas.
 * Saat API-nya tersedia, ganti fungsi di sini dengan panggilan backend (lihat moodleClient.js).
 *
 * Rujukan source Moodle: semua fungsi termasuk layanan "moodle_mobile_app"
 * ('services' => [MOODLE_OFFICIAL_MOBILE_SERVICE] di db/services.php).
 */
import { MoodleError, callWs, uploadDraftFiles } from './moodleClient';

// ---- Situs & user (lib/db/services.php)

export function getSiteInfo() {
  return callWs('core_webservice_get_site_info');
}

export async function getUserById(userId) {
  const users = await callWs('core_user_get_users_by_field', { field: 'id', values: [userId] });
  return users[0] ?? null;
}

// ---- Course

export function getUserCourses(userId) {
  return callWs('core_enrol_get_users_courses', { userid: userId, returnusercount: 0 });
}

/** classification: all | inprogress | future | past. Rujukan: filter halaman My courses di Moodle. */
export async function getCoursesByClassification(classification = 'all') {
  const res = await callWs('core_course_get_enrolled_courses_by_timeline_classification', {
    classification,
    limit: 0,
    offset: 0,
    sort: 'fullname',
  });
  return res.courses;
}

export function getRecentCourses(userId, limit = 6) {
  return callWs('core_course_get_recent_courses', { userid: userId, limit });
}

export async function getCourse(courseId) {
  const res = await callWs('core_course_get_courses_by_field', { field: 'id', value: courseId });
  return res.courses[0] ?? null;
}

export function getCourseContents(courseId) {
  return callWs('core_course_get_contents', { courseid: courseId });
}

/** Mencatat bahwa user membuka course (mengisi "Recently accessed courses"). */
export function logCourseView(courseId) {
  return callWs('core_course_view_course', { courseid: courseId }).catch(() => null);
}

export async function getAdministrationOptions(courseIds) {
  if (!courseIds.length) return [];
  const res = await callWs('core_course_get_user_administration_options', { courseids: courseIds });
  return res.courses;
}

// ---- Peserta (enrol/externallib.php)

export function getEnrolledUsers(courseId) {
  return callWs('core_enrol_get_enrolled_users', { courseid: courseId });
}

// ---- Timeline (calendar/externallib.php)

export async function getActionEvents({ from = Math.floor(Date.now() / 1000) - 14 * 86400, limit = 20 } = {}) {
  const res = await callWs('core_calendar_get_action_events_by_timesort', { timesortfrom: from, limitnum: limit });
  return res.events;
}

// ---- Nilai (grade/report/user/db/services.php)

/** Tanpa userId: dosen mendapat nilai semua mahasiswa; mahasiswa hanya miliknya. */
export async function getGradeItems(courseId, userId) {
  const res = await callWs('gradereport_user_get_grade_items', { courseid: courseId, userid: userId ?? 0 });
  return res.usergrades;
}

// ---- Aktivitas (mod/*/db/services.php)

export async function getPages(courseIds) {
  const res = await callWs('mod_page_get_pages_by_courses', { courseids: courseIds });
  return res.pages;
}

export async function getAssignments(courseIds) {
  const res = await callWs('mod_assign_get_assignments', { courseids: courseIds });
  return res.courses.flatMap((c) => c.assignments);
}

export function getSubmissionStatus(assignId) {
  return callWs('mod_assign_get_submission_status', { assignid: assignId });
}

/**
 * Simpan pengumpulan mahasiswa (mod_assign_save_submission): teks online sebagai HTML dan file lewat draft area.
 * Rujukan perilaku Moodle: tanpa pengaturan "wajib klik kirim" langsung ditandai dikumpulkan untuk dinilai.
 */
/** files: null = file tidak diubah; array entri uploadDraftFiles = isi baru area file (boleh kosong). */
export async function saveSubmission(assignId, { onlineText, files }) {
  const plugindata = {};
  if (onlineText != null) plugindata.onlinetext_editor = { text: onlineText, format: 1, itemid: 0 };
  if (files) plugindata.files_filemanager = await uploadDraftFiles(files);
  const warnings = await callWs('mod_assign_save_submission', { assignmentid: assignId, plugindata });
  if (Array.isArray(warnings) && warnings.length) throw new MoodleError(warnings[0].warningcode, warnings[0].message);
}

export function listAssignParticipants(assignId) {
  return callWs('mod_assign_list_participants', {
    assignid: assignId,
    groupid: 0,
    filter: '',
    skip: 0,
    limit: 0,
    onlyids: false,
    includeenrolments: false,
  });
}

// ---- Role

// Opsi administrasi yang hanya tersedia untuk pengajar (lihat course_get_user_administration_options()).
const TEACHER_OPTIONS = ['update', 'reports', 'backup', 'gradebook'];

/**
 * Data pengguna untuk sesi: identitas, admin situs, dan kursus yang diajar (hak per kursus).
 * Role aplikasi (DOSEN/MAHASISWA) TIDAK ditentukan di sini; sumbernya GET /auth/me backend (FE-06.3).
 */
export async function resolveSession() {
  const site = await getSiteInfo();
  const courses = await getUserCourses(site.userid);
  const options = await getAdministrationOptions(courses.map((c) => c.id));
  const teacherCourseIds = options
    .filter((c) => c.options.some((o) => o.available && TEACHER_OPTIONS.includes(o.name)))
    .map((c) => c.id);

  return {
    site: {
      name: site.sitename,
      url: site.siteurl,
      release: site.release,
    },
    user: {
      id: site.userid,
      username: site.username,
      fullname: site.fullname,
      firstname: site.firstname,
      avatar: site.userpictureurl,
      isAdmin: !!site.userissiteadmin,
      teacherCourseIds,
    },
  };
}
