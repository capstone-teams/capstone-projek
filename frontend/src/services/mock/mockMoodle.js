/**
 * Tiruan Moodle Web Service untuk mode VITE_MOODLE_MOCK=true.
 * Bentuk respons mengikuti *_returns() di source Moodle, cukup untuk kebutuhan UI.
 */

const DAY = 86400;
const now = () => Math.floor(Date.now() / 1000);
const start = now() - 21 * DAY;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const USERS = {
  3: { id: 3, username: 'dosen', firstname: 'Rina', lastname: 'Kartika', email: 'dosen@lecturer.itk.ac.id' },
  4: { id: 4, username: 'dosen2', firstname: 'Bayu', lastname: 'Pratama', email: 'dosen2@lecturer.itk.ac.id' },
  5: { id: 5, username: 'mahasiswa', firstname: 'Andi', lastname: 'Saputra', email: 'mahasiswa@student.itk.ac.id' },
  6: { id: 6, username: 'mahasiswa2', firstname: 'Siti', lastname: 'Rahmawati', email: 'mahasiswa2@student.itk.ac.id' },
  7: { id: 7, username: 'mahasiswa3', firstname: 'Dimas', lastname: 'Nugroho', email: 'mahasiswa3@student.itk.ac.id' },
  // Akun uji backend (BE-06.3); login aplikasi mewajibkan akun yang sama di backend dan Moodle.
  8: { id: 8, username: 'dosen.demo', firstname: 'Dosen', lastname: 'Demo', email: 'dosen.demo@itk.ac.id' },
  9: { id: 9, username: '11231023', firstname: 'Mahasiswa', lastname: 'Demo', email: '11231023@student.itk.ac.id' },
};
const fullname = (u) => `${u.firstname} ${u.lastname}`;
const ROLE_NAMES = { editingteacher: 'Teacher', teacher: 'Non-editing teacher', student: 'Student' };

const COURSE_DEFS = [
  {
    id: 2,
    shortname: 'IF2105',
    fullname: 'Pemrograman Web',
    category: 'Teknik Informatika',
    summary: '<p>Pengembangan aplikasi web modern: HTML, CSS, JavaScript, HTTP, REST API, dan framework berbasis komponen.</p>',
    enrol: { 3: 'editingteacher', 8: 'editingteacher', 5: 'student', 6: 'student', 7: 'student', 9: 'student' },
    weeks: [
      ['Pengantar Pemrograman Web', 'Arsitektur client-server, cara kerja browser, dan protokol HTTP.'],
      ['HTML5 dan Semantik', 'Struktur dokumen, elemen semantik, formulir, dan aksesibilitas dasar.'],
      ['CSS3 dan Layout', 'Selector, box model, Flexbox, Grid, dan responsive design.'],
      ['JavaScript Dasar', 'Variabel, fungsi, DOM, dan event.'],
      ['JavaScript Asinkron', 'Promise, async/await, dan Fetch API.'],
      ['REST API dan JSON', 'Merancang dan mengonsumsi REST API.'],
    ],
  },
  {
    id: 3,
    shortname: 'IF2203',
    fullname: 'Basis Data',
    category: 'Teknik Informatika',
    summary: '<p>Konsep basis data relasional, pemodelan ER, normalisasi, dan SQL.</p>',
    enrol: { 4: 'editingteacher', 3: 'teacher', 5: 'student', 6: 'student', 7: 'student', 9: 'student' },
    weeks: [
      ['Pengantar Basis Data', 'Konsep data, DBMS, dan arsitektur tiga level.'],
      ['Model Entity-Relationship', 'Entitas, atribut, relasi, dan kardinalitas.'],
      ['Normalisasi', 'Bentuk normal 1NF hingga BCNF.'],
      ['SQL Dasar', 'SELECT, INSERT, UPDATE, DELETE, dan JOIN.'],
    ],
  },
  {
    id: 4,
    shortname: 'IF2105-B',
    fullname: 'Pemrograman Web (Kelas B)',
    category: 'Teknik Informatika',
    summary: '<p>Kelas paralel Pemrograman Web. Materi mingguan disiapkan dengan generator AI.</p>',
    enrol: { 3: 'editingteacher', 8: 'editingteacher', 6: 'student', 7: 'student' },
    weeks: [
      ['Pengantar Pemrograman Web', 'Arsitektur client-server, cara kerja browser, dan protokol HTTP.'],
      ['HTML5 dan Semantik', 'Struktur dokumen, elemen semantik, formulir, dan aksesibilitas dasar.'],
    ],
  },
];

// ---- Bangun isi course seperti core_course_get_contents.
let cmSeq = 100;
const PAGES = [];
const ASSIGNS = [];

// Jenis pengumpulan (assignsubmission_onlinetext / assignsubmission_file), bentuk `configs` Moodle.
function assignConfigs({ onlinetext = true, wordlimit = 0, file = true, maxfiles = 20, maxbytes = 1048576 } = {}) {
  const config = (plugin, name, value) => ({ plugin, subtype: 'assignsubmission', name, value: String(value) });
  return [
    config('onlinetext', 'enabled', onlinetext ? 1 : 0),
    config('onlinetext', 'wordlimit', wordlimit),
    config('onlinetext', 'wordlimitenabled', wordlimit > 0 ? 1 : 0),
    config('file', 'enabled', file ? 1 : 0),
    config('file', 'maxfilesubmissions', maxfiles),
    config('file', 'maxsubmissionsizebytes', maxbytes),
  ];
}
const MODULE_PLURAL = { forum: 'Forums', page: 'Pages', url: 'URLs', assign: 'Assignments', quiz: 'Quizzes' };

function mod(course, section, modname, name, description, extra = {}) {
  const id = ++cmSeq;
  return {
    id,
    name,
    instance: id,
    modname,
    modplural: MODULE_PLURAL[modname],
    // Ikon asli Moodle (mod/*/pix/monologo.svg), disalin ke public/moodle/mod.
    modicon: `/moodle/mod/${modname}.svg`,
    url: `/mod/${modname}/view.php?id=${id}`,
    description,
    visible: 1,
    uservisible: true,
    indent: 0,
    contextid: 1000 + id,
    dates: [],
    ...extra,
    _course: course.id,
    _section: section,
  };
}

const CONTENTS = {};
COURSE_DEFS.forEach((c) => {
  const sections = [
    {
      id: c.id * 100,
      name: 'General',
      section: 0,
      summary: '',
      visible: 1,
      uservisible: true,
      modules: [mod(c, 0, 'forum', 'Pengumuman', '<p>Pengumuman resmi mata kuliah.</p>')],
    },
  ];
  c.weeks.forEach(([title, desc], i) => {
    const n = i + 1;
    const modules = [];
    const page = mod(c, n, 'page', `Materi: ${title}`, `<p>Bacaan utama minggu ${n}.</p>`);
    PAGES.push({
      id: page.instance,
      coursemodule: page.id,
      course: c.id,
      name: page.name,
      intro: page.description,
      content: `<h3>${title}</h3><p>${desc}</p><p>Materi ini disusun berdasarkan RPS. Pelajari contoh berikut lalu kerjakan latihan di akhir halaman.</p><ul><li>Konsep utama</li><li>Contoh penerapan</li><li>Latihan mandiri</li></ul>`,
      timemodified: start,
    });
    modules.push(page);
    if (n === 1) modules.push(mod(c, n, 'forum', 'Forum Diskusi', '<p>Tempat bertanya dan berdiskusi.</p>'));
    modules.push(mod(c, n, 'url', 'Referensi: MDN Web Docs', '<p>Referensi tambahan.</p>', { url: 'https://developer.mozilla.org' }));
    if (n % 2 === 0) {
      const due = start + n * 7 * DAY + 2 * DAY;
      const a = mod(c, n, 'assign', `Tugas ${n}: ${title}`, `<p>Kerjakan studi kasus tentang ${title} dan unggah laporan.</p>`, {
        dates: [
          { label: 'Opened:', timestamp: start + (n - 1) * 7 * DAY },
          { label: 'Due:', timestamp: due },
        ],
      });
      ASSIGNS.push({ id: a.instance, cmid: a.id, course: c.id, name: a.name, intro: a.description, duedate: due, allowsubmissionsfromdate: start + (n - 1) * 7 * DAY, grade: 100, cutoffdate: 0, configs: assignConfigs() });
      modules.push(a);
    }
    if (n === 3) {
      modules.push(
        mod(c, n, 'quiz', `Kuis ${n}`, '<p>Kuis singkat materi minggu 1-3.</p>', {
          dates: [
            { label: 'Opened:', timestamp: start + 14 * DAY },
            { label: 'Closes:', timestamp: start + 28 * DAY },
          ],
        }),
      );
    }
    sections.push({
      id: c.id * 100 + n,
      name: `Minggu ${n}: ${title}`,
      section: n,
      summary: `<p>${desc}</p>`,
      visible: 1,
      uservisible: true,
      modules,
    });
  });
  CONTENTS[c.id] = sections;
});
// Salinan awal untuk resetMockMoodle(): Edit mode mengubah CONTENTS di memori.
const INITIAL_CONTENTS = structuredClone(CONTENTS);
const INITIAL_ASSIGNS = structuredClone(ASSIGNS);

// Nilai contoh untuk tugas yang sudah lewat tenggat.
const GRADES = {};
ASSIGNS.forEach((a, k) => {
  if (a.duedate > now()) return;
  Object.entries(COURSE_DEFS.find((c) => c.id === a.course).enrol)
    .filter(([, role]) => role === 'student')
    .forEach(([uid], j) => {
      GRADES[`${a.id}:${uid}`] = 75 + ((j * 7 + k * 5) % 21);
    });
});

const tokens = new Map();
// Pengumpulan mahasiswa per `${assignId}:${userId}` dan draft area hasil webservice/upload.php.
const SUBMISSIONS = new Map();
const DRAFTS = new Map();
let draftSeq = 5000;
const recent = new Map();

function courseImage(id) {
  const hue = (id * 67) % 360;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="150"><rect width="300" height="150" fill="hsl(${hue},55%,45%)"/><g fill="hsl(${hue},55%,55%)"><circle cx="40" cy="30" r="40"/><circle cx="250" cy="120" r="60"/><rect x="120" y="50" width="70" height="70" transform="rotate(20 155 85)"/></g></svg>`;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
}

function courseSummary(c, userId) {
  const total = CONTENTS[c.id].reduce((n, s) => n + s.modules.length, 0);
  return {
    id: c.id,
    fullname: c.fullname,
    shortname: c.shortname,
    displayname: c.fullname,
    fullnamedisplay: c.fullname,
    summary: c.summary,
    summaryformat: 1,
    coursecategory: c.category,
    courseimage: courseImage(c.id),
    startdate: start,
    enddate: start + 112 * DAY,
    visible: 1,
    hidden: false,
    isfavourite: false,
    hasprogress: true,
    progress: c.enrol[userId] === 'student' ? Math.round((3 / total) * 100) : null,
    viewurl: `/course/view.php?id=${c.id}`,
    lastaccess: recent.get(`${userId}:${c.id}`) ?? null,
  };
}

function wsError(errorcode, message) {
  return { exception: 'moodle_exception', errorcode, message };
}

function userCourses(userId) {
  return COURSE_DEFS.filter((c) => c.enrol[userId]);
}

const handlers = {
  core_webservice_get_site_info(user) {
    return {
      sitename: 'Moodle ITK',
      siteurl: 'http://localhost:8080',
      release: '5.3 (mock)',
      userid: user.id,
      username: user.username,
      firstname: user.firstname,
      lastname: user.lastname,
      fullname: fullname(user),
      userpictureurl: '',
      userissiteadmin: false,
    };
  },
  core_user_get_users_by_field(_u, { values = {} }) {
    return Object.values(values)
      .map((id) => USERS[id])
      .filter(Boolean)
      .map((u) => ({ ...u, fullname: fullname(u), profileimageurl: '' }));
  },
  core_enrol_get_users_courses(_u, { userid }) {
    return userCourses(Number(userid)).map((c) => courseSummary(c, Number(userid)));
  },
  core_course_get_enrolled_courses_by_timeline_classification(user, { classification = 'all' }) {
    const list = userCourses(user.id).map((c) => courseSummary(c, user.id));
    return { courses: ['all', 'inprogress'].includes(classification) ? list : [], nextoffset: 0 };
  },
  core_course_get_recent_courses(user) {
    return userCourses(user.id)
      .filter((c) => recent.has(`${user.id}:${c.id}`))
      .map((c) => courseSummary(c, user.id))
      .sort((a, b) => b.lastaccess - a.lastaccess);
  },
  core_course_get_courses_by_field(user, { value }) {
    const c = COURSE_DEFS.find((x) => x.id === Number(value));
    if (!c) return { courses: [], warnings: [] };
    const contacts = Object.entries(c.enrol)
      .filter(([, r]) => r === 'editingteacher')
      .map(([id]) => ({ id: Number(id), fullname: fullname(USERS[id]) }));
    return { courses: [{ ...courseSummary(c, user.id), categoryname: c.category, format: 'topics', contacts }], warnings: [] };
  },
  core_course_get_contents(user, { courseid }) {
    const c = COURSE_DEFS.find((x) => x.id === Number(courseid));
    if (!c?.enrol[user.id]) return wsError('requireloginerror', 'Course or activity not accessible. (Not enrolled)');
    // Mahasiswa tidak dapat membuka section/aktivitas yang disembunyikan (uservisible=false).
    const student = c.enrol[user.id] === 'student';
    return CONTENTS[c.id].map((s) => {
      const sectionVisible = !student || s.visible === 1;
      return {
        ...s,
        uservisible: sectionVisible,
        modules: s.modules.map(({ _course, _section, ...m }) => ({ ...m, uservisible: sectionVisible && (!student || m.visible === 1) })),
      };
    });
  },
  core_course_view_course(user, { courseid }) {
    recent.set(`${user.id}:${courseid}`, now());
    return { status: true, warnings: [] };
  },
  core_course_get_user_administration_options(user, { courseids = {} }) {
    return {
      courses: Object.values(courseids).map((id) => {
        const role = COURSE_DEFS.find((c) => c.id === Number(id))?.enrol[user.id];
        const teacher = role === 'editingteacher' || role === 'teacher';
        const edit = role === 'editingteacher';
        return {
          id: Number(id),
          options: [
            { name: 'update', available: edit },
            { name: 'reports', available: teacher },
            { name: 'gradebook', available: edit },
            { name: 'badges', available: true },
          ],
        };
      }),
      warnings: [],
    };
  },
  core_enrol_get_enrolled_users(_u, { courseid }) {
    const c = COURSE_DEFS.find((x) => x.id === Number(courseid));
    return Object.entries(c?.enrol ?? {}).map(([id, role]) => {
      const u = USERS[id];
      return {
        id: u.id,
        username: u.username,
        fullname: fullname(u),
        email: u.email,
        profileimageurl: '',
        lastcourseaccess: recent.get(`${id}:${c.id}`) ?? 0,
        roles: [{ roleid: 1, shortname: role, name: ROLE_NAMES[role] }],
      };
    });
  },
  core_calendar_get_action_events_by_timesort(user) {
    const events = ASSIGNS.filter((a) => COURSE_DEFS.find((c) => c.id === a.course).enrol[user.id])
      .filter((a) => a.duedate > now() - 7 * DAY)
      .map((a) => {
        const c = COURSE_DEFS.find((x) => x.id === a.course);
        const isStudent = c.enrol[user.id] === 'student';
        return {
          id: a.id,
          name: `${a.name} is due`,
          activityname: a.name,
          modulename: 'assign',
          instance: a.id,
          timesort: a.duedate,
          overdue: a.duedate < now(),
          course: { id: c.id, fullname: c.fullname, fullnamedisplay: c.fullname },
          url: `/mod/assign/view.php?id=${a.cmid}`,
          action: { name: isStudent ? 'Add submission' : 'Grade', actionable: true, itemcount: isStudent ? 1 : 3 },
        };
      })
      .sort((a, b) => a.timesort - b.timesort);
    return { events, firstid: events[0]?.id ?? 0, lastid: events.at(-1)?.id ?? 0 };
  },
  gradereport_user_get_grade_items(user, { courseid, userid }) {
    const c = COURSE_DEFS.find((x) => x.id === Number(courseid));
    const isTeacher = ['editingteacher', 'teacher'].includes(c?.enrol[user.id]);
    const target = Number(userid) || (isTeacher ? 0 : user.id);
    if (!isTeacher && target !== user.id) return wsError('nopermissions', 'Sorry, but you do not currently have permissions to do that.');
    const students = Object.entries(c.enrol)
      .filter(([id, r]) => r === 'student' && (!target || Number(id) === target))
      .map(([id]) => USERS[id]);
    const assigns = ASSIGNS.filter((a) => a.course === c.id);
    return {
      usergrades: students.map((s) => {
        const items = assigns.map((a) => {
          const g = GRADES[`${a.id}:${s.id}`];
          return {
            id: a.id,
            itemname: a.name,
            itemtype: 'mod',
            itemmodule: 'assign',
            cmid: a.cmid,
            graderaw: g ?? null,
            gradeformatted: g != null ? g.toFixed(2) : '-',
            grademin: 0,
            grademax: 100,
            percentageformatted: g != null ? `${g.toFixed(2)} %` : '-',
            feedback: g != null ? '<p>Kerja bagus.</p>' : '',
          };
        });
        const graded = items.filter((i) => i.graderaw != null);
        const total = graded.reduce((n, i) => n + i.graderaw, 0);
        const max = graded.length * 100;
        items.push({
          id: 9000 + c.id,
          itemname: null,
          itemtype: 'course',
          graderaw: graded.length ? total : null,
          gradeformatted: graded.length ? total.toFixed(2) : '-',
          grademin: 0,
          grademax: max || 100,
          percentageformatted: graded.length ? `${((total / max) * 100).toFixed(2)} %` : '-',
          feedback: '',
        });
        return { courseid: c.id, userid: s.id, userfullname: fullname(s), gradeitems: items };
      }),
      warnings: [],
    };
  },
  mod_page_get_pages_by_courses(_u, { courseids = {} }) {
    const ids = Object.values(courseids).map(Number);
    return { pages: PAGES.filter((p) => ids.includes(p.course)), warnings: [] };
  },
  mod_assign_get_assignments(_u, { courseids = {} }) {
    const ids = Object.values(courseids).map(Number);
    return { courses: ids.map((id) => ({ id, assignments: ASSIGNS.filter((a) => a.course === id) })), warnings: [] };
  },
  mod_assign_get_submission_status(user, { assignid }) {
    const a = ASSIGNS.find((x) => x.id === Number(assignid));
    const g = GRADES[`${a.id}:${user.id}`];
    const saved = SUBMISSIONS.get(`${a.id}:${user.id}`);
    const plugins = saved
      ? [
          { type: 'onlinetext', name: 'Online text', editorfields: [{ name: 'onlinetext', text: saved.text, format: 1 }] },
          {
            type: 'file',
            name: 'File submissions',
            fileareas: [{
              area: 'submission_files',
              files: saved.files.map((f) => ({ filename: f.filename, filepath: f.filepath ?? '/', filesize: f.filesize, timemodified: f.timemodified ?? saved.timemodified, fileurl: '' })),
            }],
          },
        ]
      : [];
    return {
      lastattempt: {
        submission: {
          status: saved ? 'submitted' : g != null ? 'submitted' : 'new',
          timemodified: saved?.timemodified ?? (g != null ? a.duedate - DAY : 0),
          plugins,
        },
        gradingstatus: g != null ? 'graded' : 'notgraded',
        caneditowner: a.duedate > now(),
        canedit: !a.cutoffdate || a.cutoffdate > now(),
      },
      feedback: g != null ? { gradefordisplay: `${g.toFixed(2)} / 100.00` } : undefined,
      warnings: [],
    };
  },
  core_files_get_unused_draft_itemid() {
    const itemid = ++draftSeq;
    DRAFTS.set(itemid, []);
    return { itemid, warnings: [] };
  },
  mod_assign_save_submission(user, { assignmentid, plugindata = {} }) {
    const a = ASSIGNS.find((x) => x.id === Number(assignmentid));
    if (!a) return wsError('invalidrecord', 'Can not find data record in database.');
    if (COURSE_DEFS.find((c) => c.id === a.course)?.enrol[user.id] !== 'student') {
      return wsError('nopermissions', 'Sorry, but you do not currently have permissions to do that (Submit assignment).');
    }
    if (a.allowsubmissionsfromdate > now()) return [{ item: 'assignment', itemid: a.id, warningcode: 'couldnotsavesubmission', message: 'Pengumpulan belum dibuka.' }];
    const config = (plugin, name) => Number(a.configs.find((c) => c.plugin === plugin && c.name === name)?.value ?? 0);
    const previous = SUBMISSIONS.get(`${a.id}:${user.id}`);
    // Seperti file_postupdate_standard_filemanager: tanpa draft itemid, file lama tidak diubah.
    const text = plugindata.onlinetext_editor ? plugindata.onlinetext_editor.text ?? '' : previous?.text ?? '';
    const words = text.replace(/<[^>]*>/g, ' ').trim().split(/\s+/).filter(Boolean).length;
    if (config('onlinetext', 'wordlimit') > 0 && words > config('onlinetext', 'wordlimit')) {
      return [{ item: 'assignment', itemid: a.id, warningcode: 'couldnotsavesubmission', message: `Batas kata terlampaui (${words}/${config('onlinetext', 'wordlimit')}).` }];
    }
    const files = Number(plugindata.files_filemanager) ? DRAFTS.get(Number(plugindata.files_filemanager)) ?? [] : previous?.files ?? [];
    if (files.length > config('file', 'maxfilesubmissions') || files.some((f) => f.filesize > config('file', 'maxsubmissionsizebytes'))) {
      return [{ item: 'assignment', itemid: a.id, warningcode: 'couldnotsavesubmission', message: 'File melebihi batas jumlah atau ukuran.' }];
    }
    SUBMISSIONS.set(`${a.id}:${user.id}`, { text, files, timemodified: now() });
    return [];
  },
  mod_assign_list_participants(_u, { assignid }) {
    const a = ASSIGNS.find((x) => x.id === Number(assignid));
    const c = COURSE_DEFS.find((x) => x.id === a.course);
    return Object.entries(c.enrol)
      .filter(([, r]) => r === 'student')
      .map(([id]) => ({
        id: Number(id),
        fullname: fullname(USERS[id]),
        submitted: GRADES[`${a.id}:${id}`] != null,
        requiregrading: false,
        grantedextension: false,
      }));
  },
};

// ---- Editor kursus (Edit mode). Mengikuti core_courseformat\stateactions dan
// core_update_inplace_editable pada Moodle 5.x; hanya editingteacher yang boleh mengubah.

function editableCourse(user, courseid) {
  const c = COURSE_DEFS.find((x) => x.id === Number(courseid));
  if (!c?.enrol[user.id]) return { error: wsError('requireloginerror', 'Course or activity not accessible. (Not enrolled)') };
  if (c.enrol[user.id] !== 'editingteacher') {
    return { error: wsError('nopermissions', 'Sorry, but you do not currently have permissions to do that (Manage activities).') };
  }
  return { course: c, sections: CONTENTS[c.id] };
}

function findCm(sections, cmid) {
  for (const section of sections) {
    const index = section.modules.findIndex((m) => m.id === Number(cmid));
    if (index !== -1) return { section, index, cm: section.modules[index] };
  }
  return null;
}

const CM_ACTIONS = {
  cm_hide: (found) => { found.cm.visible = 0; },
  cm_show: (found) => { found.cm.visible = 1; },
  cm_moveright: (found) => { found.cm.indent = Math.min((found.cm.indent ?? 0) + 1, 16); },
  cm_moveleft: (found) => { found.cm.indent = Math.max((found.cm.indent ?? 0) - 1, 0); },
  cm_delete: (found) => { found.section.modules.splice(found.index, 1); },
  cm_duplicate: (found) => {
    const id = ++cmSeq;
    const copy = { ...structuredClone(found.cm), id, instance: id, name: `${found.cm.name} (copy)`, contextid: 1000 + id };
    copy.url = `/mod/${copy.modname}/view.php?id=${id}`;
    const page = PAGES.find((p) => p.coursemodule === found.cm.id);
    if (page) PAGES.push({ ...page, id, coursemodule: id, name: copy.name });
    found.section.modules.splice(found.index + 1, 0, copy);
  },
};

function moveCm(sections, found, targetsectionid, targetcmid) {
  const target = sections.find((s) => s.id === Number(targetsectionid))
    ?? (targetcmid ? findCm(sections, targetcmid)?.section : null);
  if (!target) return wsError('invalidparameter', 'Target section tidak ditemukan.');
  found.section.modules.splice(found.index, 1);
  const before = targetcmid ? target.modules.findIndex((m) => m.id === Number(targetcmid)) : -1;
  target.modules.splice(before === -1 ? target.modules.length : before, 0, found.cm);
  return null;
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
}

const editingHandlers = {
  core_courseformat_update_course(user, { action, courseid, ids = [], targetsectionid, targetcmid }) {
    const { error, course, sections } = editableCourse(user, courseid);
    if (error) return error;
    const targets = Object.values(ids).map(Number);
    if (action === 'section_add') {
      const number = sections.length;
      sections.push({ id: course.id * 100 + number, name: 'New section', section: number, summary: '', visible: 1, uservisible: true, modules: [] });
      return '[]';
    }
    if (action === 'section_hide' || action === 'section_show') {
      for (const id of targets) {
        const section = sections.find((s) => s.id === id);
        if (!section) return wsError('invalidrecord', 'Section tidak ditemukan.');
        if (section.section === 0 && action === 'section_hide') return wsError('cannothidesection', 'Section umum tidak dapat disembunyikan.');
        section.visible = action === 'section_hide' ? 0 : 1;
      }
      return '[]';
    }
    if (action !== 'cm_move' && !CM_ACTIONS[action]) return wsError('invalidparameter', `Aksi ${action} tidak didukung mock.`);
    for (const id of targets) {
      const found = findCm(sections, id);
      if (!found) return wsError('invalidrecord', 'Aktivitas tidak ditemukan.');
      if (action === 'cm_move') {
        const moveError = moveCm(sections, found, targetsectionid, targetcmid);
        if (moveError) return moveError;
      } else {
        CM_ACTIONS[action](found);
      }
    }
    return '[]';
  },
  core_update_inplace_editable(user, { component, itemtype, itemid, value }) {
    const name = String(value ?? '').trim();
    if (!name) return wsError('invalidparameter', 'Nama tidak boleh kosong.');
    const courseId = itemtype === 'activityname'
      ? Object.keys(CONTENTS).find((id) => findCm(CONTENTS[id], itemid))
      : Object.keys(CONTENTS).find((id) => CONTENTS[id].some((s) => s.id === Number(itemid)));
    const { error, sections } = editableCourse(user, courseId);
    if (error) return error;
    if (component === 'core_course' && itemtype === 'activityname') {
      findCm(sections, itemid).cm.name = name;
    } else if (/^format_/.test(component) && itemtype === 'sectionname') {
      sections.find((s) => s.id === Number(itemid)).name = name;
    } else {
      return wsError('invalidparameter', `Item ${component}/${itemtype} tidak didukung mock.`);
    }
    return { component, itemtype, itemid: Number(itemid), displayvalue: name, value: name, editlabel: '', edithint: '' };
  },
  // Bukan fungsi Moodle: Moodle core belum punya Web Service untuk membuat assign/label
  // beserta isinya (core_courseformat_create_module hanya untuk modul FEATURE_QUICKCREATE).
  mock_course_create_activity(user, { courseid, sectionnum, modname, name, intro = '', text = '', allowsubmissionsfromdate = 0, duedate = 0, cutoffdate = 0, grade = 100, timeopen = 0, timeclose = 0, onlinetext_enabled = 0, onlinetext_wordlimit = 0, file_enabled = 1, file_maxfiles = 20, file_maxbytes = 1048576, format = 0 }) {
    const { error, course, sections } = editableCourse(user, courseid);
    if (error) return error;
    const section = sections.find((s) => s.section === Number(sectionnum));
    if (!section) return wsError('invalidrecord', 'Section tidak ditemukan.');
    if (modname === 'assign') {
      if (!String(name ?? '').trim()) return wsError('invalidparameter', 'Nama tugas wajib diisi.');
      const opens = Number(allowsubmissionsfromdate) || 0;
      const due = Number(duedate) || 0;
      if (opens && due && due <= opens) return wsError('invalidparameter', 'Tenggat harus setelah tanggal dibuka.');
      const cutoff = Number(cutoffdate) || 0;
      if (cutoff && ((due && cutoff < due) || (opens && cutoff < opens))) return wsError('invalidparameter', 'Cut-off date cannot be earlier than the due date.');
      const dates = [...(opens ? [{ label: 'Opened:', timestamp: opens }] : []), ...(due ? [{ label: 'Due:', timestamp: due }] : [])];
      const cm = mod(course, section.section, 'assign', name.trim(), intro, { dates });
      const configs = assignConfigs({
        onlinetext: !!Number(onlinetext_enabled),
        wordlimit: Number(onlinetext_wordlimit) || 0,
        file: !!Number(file_enabled),
        maxfiles: Number(file_maxfiles) || 20,
        maxbytes: Number(file_maxbytes) || 1048576,
      });
      ASSIGNS.push({ id: cm.instance, cmid: cm.id, course: course.id, name: cm.name, intro, duedate: due, allowsubmissionsfromdate: opens, grade: Number(grade) || 100, cutoffdate: cutoff, configs });
      section.modules.push(cm);
      return { cmid: cm.id };
    }
    if (modname === 'quiz') {
      if (!String(name ?? '').trim()) return wsError('invalidparameter', 'Nama kuis wajib diisi.');
      const opens = Number(timeopen) || 0;
      const closes = Number(timeclose) || 0;
      if (opens && closes && closes <= opens) return wsError('invalidparameter', 'Waktu ditutup harus setelah waktu dibuka.');
      const dates = [...(opens ? [{ label: 'Opened:', timestamp: opens }] : []), ...(closes ? [{ label: 'Closes:', timestamp: closes }] : [])];
      const cm = mod(course, section.section, 'quiz', name.trim(), intro, { dates });
      section.modules.push(cm);
      return { cmid: cm.id };
    }
    if (modname === 'label') {
      // format 1 (FORMAT_HTML) dari editor; selain itu teks biasa yang diubah menjadi paragraf.
      const html = Number(format) === 1
        ? String(text ?? '')
        : String(text ?? '').trim().split(/\n{2,}/).map((p) => `<p>${escapeHtml(p).replace(/\n/g, '<br>')}</p>`).join('');
      const plain = html.replace(/<br\s*\/?>/gi, ' ').replace(/<[^>]*>/g, ' ').replace(/&nbsp;/g, ' ').trim();
      if (!plain) return wsError('invalidparameter', 'Isi teks wajib diisi.');
      // Seperti Moodle: tanpa "Title in course index", nama label diambil dari awal isinya.
      const cm = mod(course, section.section, 'label', String(name ?? '').trim() || plain.replace(/\s+/g, ' ').slice(0, 50), html);
      section.modules.push(cm);
      return { cmid: cm.id };
    }
    return wsError('invalidparameter', `Jenis aktivitas ${modname} belum didukung.`);
  },
};
Object.assign(handlers, editingHandlers);

/** Kembalikan isi kursus mock ke kondisi awal (untuk test). */
export function resetMockMoodle() {
  Object.keys(CONTENTS).forEach((id) => { CONTENTS[id] = structuredClone(INITIAL_CONTENTS[id]); });
  ASSIGNS.splice(0, ASSIGNS.length, ...structuredClone(INITIAL_ASSIGNS));
  SUBMISSIONS.clear();
  DRAFTS.clear();
}

export async function mockRequestToken(username, password) {
  await sleep(200);
  const user = Object.values(USERS).find((u) => u.username === username);
  if (!user || password !== `${username}123`) {
    const { MoodleError } = await import('../moodle/moodleClient');
    throw new MoodleError('invalidlogin', 'Invalid login, please try again');
  }
  const token = `mock-${user.id}-${Date.now()}`;
  tokens.set(token, user.id);
  return token;
}

/**
 * Tiruan webservice/upload.php: simpan metadata file ke draft area (baru bila itemid 0) pada filepath
 * dan kembalikan itemid-nya. files: [{ name, size }].
 */
export async function mockUploadDraftFiles(token, files, { itemid = 0, filepath = '/' } = {}) {
  await sleep(150);
  if (!USERS[tokens.get(token) ?? Number(token.split('-')[1])]) return { error: 'Invalid token - token not found', errorcode: 'invalidtoken' };
  const id = itemid > 0 ? itemid : ++draftSeq;
  const draft = DRAFTS.get(id) ?? [];
  draft.push(...files.map((file) => ({ filename: file.name, filepath, filesize: file.size, timemodified: now() })));
  DRAFTS.set(id, draft);
  return files.map((file) => ({ itemid: id, filename: file.name, filepath, filesize: file.size, filearea: 'draft' }));
}

export async function mockCallWs(token, wsfunction, params) {
  await sleep(150);
  const userId = tokens.get(token) ?? Number(token.split('-')[1]);
  const user = USERS[userId];
  if (!user) return wsError('invalidtoken', 'Invalid token - token not found');
  const handler = handlers[wsfunction];
  if (!handler) return wsError('accessexception', `Access control exception (${wsfunction} tidak tersedia di mock)`);
  return structuredClone(handler(user, params));
}
