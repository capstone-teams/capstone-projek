/**
 * Data kursus yang belum punya API backend: kursus, peserta, nilai, aktivitas, dan pengumpulan tugas.
 * Saat API-nya tersedia, ganti fungsi di sini dengan panggilan backend (lihat moodleClient.js).
 *
 * Rujukan source Moodle: semua fungsi termasuk layanan "moodle_mobile_app"
 * ('services' => [MOODLE_OFFICIAL_MOBILE_SERVICE] di db/services.php).
 */
import { api } from '../apiClient';
import { MoodleError, callWs, uploadDraftFiles } from './moodleClient';

// Helper untuk mengambil daftar kursus dari Backend Gateway (/api/v1/courses atau /api/v1/integrations/moodle/courses)
async function fetchGatewayCourses() {
  const res = (await api.get('/courses').catch(() => null))
    ?? (await api.get('/integrations/moodle/courses').catch(() => null));
  return res?.items ?? res?.courses ?? [];
}

// Situs & user

export function getSiteInfo() {
  return callWs('core_webservice_get_site_info');
}

export async function getUserById(userId) {
  const users = await callWs('core_user_get_users_by_field', { field: 'id', values: [userId] });
  return users[0] ?? null;
}

// Kursus

export function getUserCourses(userId) {
  return callWs('core_enrol_get_users_courses', { userid: userId, returnusercount: 0 });
}

/** classification: all | inprogress | future | past. Rujukan: filter halaman My courses di Moodle. */
export async function getCoursesByClassification(classification = 'all') {
  try {
    const res = await callWs('core_course_get_enrolled_courses_by_timeline_classification', {
      classification,
      limit: 0,
      offset: 0,
      sort: 'fullname',
    });
    return res.courses;
  } catch (err) {
    // Single Gateway: jika Moodle WS client tidak memiliki sesi/token langsung di browser,
    // ambil daftar kursus dari Backend Gateway (/api/v1/courses atau /api/v1/integrations/moodle/courses)
    const courses = await fetchGatewayCourses();
    if (courses.length > 0) return courses;
    throw err;
  }
}

export function getRecentCourses(userId, limit = 6) {
  return callWs('core_course_get_recent_courses', { userid: userId, limit }).catch(async (err) => {
    const courses = await fetchGatewayCourses();
    if (courses.length > 0) return courses.slice(0, limit);
    throw err;
  });
}

export async function getCourse(courseId) {
  try {
    const res = await callWs('core_course_get_courses_by_field', { field: 'id', value: courseId });
    return res.courses[0] ?? null;
  } catch (err) {
    const byId = await api.get(`/courses/${courseId}`).catch(() => null);
    if (byId) {
      return {
        ...byId,
        summary: byId.summary || byId.description || '',
      };
    }
    const courses = await fetchGatewayCourses();
    const found = courses.find((c) => String(c.id) === String(courseId) || String(c.moodle_course_id) === String(courseId));
    if (found) {
      return {
        ...found,
        summary: found.summary || found.description || '',
      };
    }
    throw err;
  }
}

export async function getCourseContents(courseId) {
  try {
    return await callWs('core_course_get_contents', { courseid: courseId });
  } catch {
    // Single Gateway: jika kursus belum dieksekusi ke Moodle atau token Moodle tidak ada di browser,
    // ambil konten atau rencana kursus dari Backend Gateway.
    const content = await api.get(`/courses/${courseId}/content`).catch(() => null);
    if (content?.weeks?.length) {
      return content.weeks.map((w) => ({
        id: w.week,
        section: w.week,
        name: `Minggu ${w.week}: ${w.topic || 'Materi'}`,
        summary: w.learning_objectives?.length
          ? `<p><strong>Capaian Pembelajaran:</strong> ${w.learning_objectives.join(', ')}</p>`
          : '',
        summaryformat: 1,
        visible: 1,
        uservisible: true,
        modules: (w.materials ?? []).map((m, idx) => ({
          id: m.content_id || `${w.week}-${idx + 1}`,
          name: m.title || `Materi Minggu ${w.week}`,
          modname: m.type === 'quiz' ? 'quiz' : m.type === 'assignment' ? 'assign' : 'page',
          uservisible: true,
          visible: 1,
        })),
      }));
    }
    const plan = await api.get(`/courses/${courseId}/plan`).catch(() => null);
    if (plan?.weeks?.length) {
      return plan.weeks.map((w) => ({
        id: w.week_number,
        section: w.week_number,
        name: `Minggu ${w.week_number}: ${w.title}`,
        summary: w.topics?.length ? `<p><strong>Topik:</strong> ${w.topics.join(', ')}</p>` : '',
        summaryformat: 1,
        visible: 1,
        uservisible: true,
        modules: w.assessment
          ? [
              {
                id: `assessment-${w.week_number}`,
                name: `${w.assessment.type || 'Tugas'}: ${w.assessment.description || ''}`,
                modname: w.assessment.type === 'kuis' ? 'quiz' : 'assign',
                uservisible: true,
                visible: 1,
              },
            ]
          : [],
      }));
    }
    return [];
  }
}

/** Mencatat bahwa user membuka course (mengisi "Recently accessed courses"). */
export function logCourseView(courseId) {
  return callWs('core_course_view_course', { courseid: courseId }).catch(() => null);
}

export async function getAdministrationOptions(courseIds) {
  if (!courseIds.length) return [];
  try {
    const res = await callWs('core_course_get_user_administration_options', { courseids: courseIds });
    return res.courses;
  } catch {
    return courseIds.map((id) => ({
      id,
      options: [
        { name: 'update', available: true },
        { name: 'reports', available: true },
        { name: 'gradebook', available: true },
      ],
    }));
  }
}

export function getEnrolledUsers(courseId) {
  return callWs('core_enrol_get_enrolled_users', { courseid: courseId }).catch(() => []);
}

export async function getActionEvents({ from = Math.floor(Date.now() / 1000) - 14 * 86400, limit = 20 } = {}) {
  try {
    const res = await callWs('core_calendar_get_action_events_by_timesort', { timesortfrom: from, limitnum: limit });
    return res.events;
  } catch {
    return [];
  }
}

/** Tanpa userId: dosen mendapat nilai semua mahasiswa; mahasiswa hanya miliknya. */
export async function getGradeItems(courseId, userId) {
  try {
    const res = await callWs('gradereport_user_get_grade_items', { courseid: courseId, userid: userId ?? 0 });
    return res.usergrades ?? [];
  } catch {
    return [];
  }
}

export async function getPages(courseIds) {
  try {
    const res = await callWs('mod_page_get_pages_by_courses', { courseids: courseIds });
    return res.pages ?? [];
  } catch {
    return [];
  }
}

export async function getAssignments(courseIds) {
  try {
    const res = await callWs('mod_assign_get_assignments', { courseids: courseIds });
    return res.courses?.flatMap((c) => c.assignments) ?? [];
  } catch {
    return [];
  }
}

export function getSubmissionStatus(assignId) {
  return callWs('mod_assign_get_submission_status', { assignid: assignId });
}

/**
 * Simpan pengumpulan mahasiswa (mod_assign_save_submission): teks online sebagai HTML dan file lewat draft area.
 * Rujukan perilaku Moodle: tanpa pengaturan "wajib klik kirim" langsung ditandai dikumpulkan untuk dinilai.
 */
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
  }).catch(() => []);
}

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
