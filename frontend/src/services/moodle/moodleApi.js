/**
 * Data kursus yang belum punya API backend: kursus, peserta, nilai, aktivitas, dan pengumpulan tugas.
 * Saat API-nya tersedia, ganti fungsi di sini dengan panggilan backend (lihat moodleClient.js).
 *
 * Rujukan source Moodle: semua fungsi termasuk layanan "moodle_mobile_app"
 * ('services' => [MOODLE_OFFICIAL_MOBILE_SERVICE] di db/services.php).
 */
import { api } from '../apiClient';
import { MoodleError, callWs, uploadDraftFiles } from './moodleClient';
import { isMoodleCourseId } from '../../utils/courseId';

// Daftar kursus dari Backend Gateway: kursus Moodle lewat integrasi (/integrations/moodle/courses) lebih dulu, lalu
// project kursus backend (/courses). Bila integrasi Moodle gagal dan tidak ada project, galatnya diteruskan (pesannya
// sudah ramah pengguna dari apiClient) agar halaman menampilkan gangguan, bukan "belum ada kursus".
async function loadGatewayCourses() {
  let moodleError = null;
  const moodleRes = await api.get('/integrations/moodle/courses').catch((error) => {
    moodleError = error;
    return null;
  });
  if (moodleRes?.courses?.length) {
    return moodleRes.courses.map((c) => ({
      ...c,
      id: c.moodle_course_id ?? c.id,
      summary: c.summary ?? '',
      category: c.category ?? null,
    }));
  }
  const legacyRes = await api.get('/courses', { ignoreForbidden: true }).catch(() => null);
  const items = legacyRes?.items ?? legacyRes?.courses ?? [];
  if (!items.length && moodleError) throw moodleError;
  return items;
}

// Beberapa bagian halaman (dasbor, kursus berjalan, kursus terakhir) meminta daftar yang sama bersamaan: selama
// permintaan masih berjalan, permintaan itu dipakai bersama. Hasilnya tidak disimpan, jadi pemanggilan berikutnya
// (termasuk "Coba lagi") selalu mengambil data terbaru.
let pendingGatewayCourses = null;

function fetchGatewayCourses() {
  if (!pendingGatewayCourses) {
    pendingGatewayCourses = loadGatewayCourses().finally(() => {
      pendingGatewayCourses = null;
    });
  }
  return pendingGatewayCourses;
}

/** Section dari GET /integrations/moodle/courses/{id}/contents dalam bentuk core_course_get_contents. */
function fromMoodleSection(section) {
  return {
    id: section.moodle_section_id,
    section: section.section_number,
    name: section.name || (section.section_number === 0 ? 'Umum' : `Pertemuan ${section.section_number}`),
    summary: section.summary ?? '',
    summaryformat: 1,
    visible: section.visible === false ? 0 : 1,
    uservisible: true,
    modules: (section.modules ?? []).map((module) => ({
      id: module.moodle_module_id,
      name: module.name,
      modname: module.modname,
      description: module.description ?? '',
      url: module.url ?? null,
      content: module.content ?? null,
      visible: module.visible === false ? 0 : 1,
      uservisible: true,
    })),
  };
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
    // Single Gateway: tanpa sesi Moodle di browser, daftar kursus diambil dari Backend Gateway. Galat sesi Moodle
    // browser (`err`) tidak relevan bagi pengguna, jadi yang diteruskan adalah hasil atau galat gateway.
    if (!(err instanceof MoodleError)) throw err;
    return fetchGatewayCourses();
  }
}

export function getRecentCourses(userId, limit = 6) {
  return callWs('core_course_get_recent_courses', { userid: userId, limit }).catch(async (err) => {
    if (!(err instanceof MoodleError)) throw err;
    return (await fetchGatewayCourses()).slice(0, limit);
  });
}

export async function getCourse(courseId) {
  try {
    const res = await callWs('core_course_get_courses_by_field', { field: 'id', value: courseId });
    return res.courses[0] ?? null;
  } catch (err) {
    // Kursus Moodle (ID angka) lewat integrasi; /courses/{id} hanya menerima ID project backend.
    const byId = isMoodleCourseId(courseId)
      ? await api.get(`/integrations/moodle/courses/${courseId}`).then((c) => ({ ...c, id: c.moodle_course_id ?? c.id }), () => null)
      : await api.get(`/courses/${courseId}`).catch(() => null);
    if (byId) {
      return {
        ...byId,
        summary: byId.summary || byId.description || '',
      };
    }
    const courses = await fetchGatewayCourses();
    const found = courses.find((c) => String(c.id) === String(courseId) || String(c.moodle_course_id) === String(courseId) || String(c.shortname).toLowerCase() === String(courseId).toLowerCase());
    if (found) {
      return {
        ...found,
        summary: found.summary || found.description || '',
      };
    }
    throw err;
  }
}

const escapeHtml = (text) => String(text ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
const htmlList = (items) => `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;

/** Ringkasan pertemuan seperti LMS ITK: Sub-CPMK lalu Bahan Kajian. */
function weekSummary({ subCpmk = [], topics = [] }) {
  const parts = [];
  if (subCpmk.length) parts.push(`<p><strong>Sub-CPMK:</strong></p>${htmlList(subCpmk)}`);
  if (topics.length) parts.push(`<p><strong>Bahan Kajian:</strong></p>${htmlList(topics)}`);
  return parts.join('');
}

const MATERIAL_MODNAME = { quiz: 'quiz', assignment: 'assign' };

export async function getCourseContents(courseId) {
  try {
    return await callWs('core_course_get_contents', { courseid: courseId });
  } catch {
    // Single Gateway: tanpa token Moodle di browser, isi kursus diambil dari Backend Gateway.
    // Kursus Moodle: section dan modul apa adanya dari GET /integrations/moodle/courses/{id}/contents.
    if (isMoodleCourseId(courseId)) {
      const contents = await api.get(`/integrations/moodle/courses/${courseId}/contents`).catch(() => null);
      return (contents?.sections ?? []).map(fromMoodleSection);
    }
    // Project kursus backend: konten mingguan (GET /courses/{id}/content) memberi aktivitas, rencana
    // (GET /courses/{id}/plan) memberi Sub-CPMK dan bahan kajian; keduanya digabung per pertemuan.
    const [content, plan] = await Promise.all([
      api.get(`/courses/${courseId}/content`).catch(() => null),
      api.get(`/courses/${courseId}/plan`).catch(() => null),
    ]);
    const planWeeks = new Map((plan?.weeks ?? []).map((w) => [w.week_number, w]));
    const planSummary = (w) => weekSummary({ subCpmk: [...(w.learning_outcomes ?? []), ...(w.objectives ?? [])], topics: w.topics?.length ? w.topics : [w.title].filter(Boolean) });
    const section = (number, title, summary, modules) => ({
      id: number,
      section: number,
      name: `Pertemuan ${number}: ${title}`,
      summary,
      summaryformat: 1,
      visible: 1,
      uservisible: true,
      modules,
    });

    if (content?.weeks?.length) {
      return content.weeks.map((w) => {
        const planned = planWeeks.get(w.week);
        return section(
          w.week,
          w.topic || planned?.title || 'Materi',
          planned ? planSummary(planned) : weekSummary({ subCpmk: w.learning_objectives ?? [], topics: [w.topic].filter(Boolean) }),
          (w.materials ?? []).map((m, idx) => ({
            id: m.content_id || `${w.week}-${idx + 1}`,
            name: m.title || `Materi pertemuan ${w.week}`,
            modname: MATERIAL_MODNAME[m.type] ?? 'page',
            uservisible: true,
            visible: 1,
          })),
        );
      });
    }
    if (planWeeks.size) {
      return [...planWeeks.values()].map((w) => section(
        w.week_number,
        w.title,
        planSummary(w),
        w.assessment
          ? [{
              id: `assessment-${w.week_number}`,
              name: `${w.assessment.type || 'Tugas'}: ${w.assessment.description || ''}`,
              modname: w.assessment.type === 'kuis' ? 'quiz' : 'assign',
              uservisible: true,
              visible: 1,
            }]
          : [],
      ));
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
    // Tanpa sesi Moodle di browser hak per kursus tidak diketahui. Jangan anggap tersedia: mahasiswa tidak boleh
    // mendapat mode edit; dosen tetap dapat mengedit lewat role backend (lihat MoodleCourseLayout).
    return courseIds.map((id) => ({
      id,
      options: [
        { name: 'update', available: false },
        { name: 'reports', available: false },
        { name: 'gradebook', available: false },
      ],
    }));
  }
}

/** Peserta terdaftar. Gateway backend lebih dulu; Moodle langsung hanya bila VITE_MOODLE_URL dikonfigurasi. */
export function getEnrolledUsers(courseId) {
  return api
    .get(`/integrations/moodle/courses/${courseId}/participants`)
    .then((res) => res?.participants ?? [])
    .catch(() =>
      callWs('core_enrol_get_enrolled_users', { courseid: courseId })
        .then((users) =>
          (users ?? []).map((u) => ({
            id: u.id,
            fullname: u.fullname,
            email: u.email ?? '',
            profileimageurl: u.profileimageurl,
            lastcourseaccess: u.lastcourseaccess,
            roles: (u.roles ?? []).map((r) => ({ shortname: r.shortname, name: r.name ?? r.shortname })),
          })),
        )
        .catch(() => []),
    );
}

/** Daftarkan akun Moodle yang sudah ada (dicari lewat email/username) ke course. */
export function addMoodleParticipant(courseId, { query, role = 'student' }) {
  return api.post(`/integrations/moodle/courses/${courseId}/participants`, { query, role });
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
