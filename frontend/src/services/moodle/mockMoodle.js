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
    enrol: { 3: 'editingteacher', 5: 'student', 6: 'student', 7: 'student' },
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
    enrol: { 4: 'editingteacher', 3: 'teacher', 5: 'student', 6: 'student', 7: 'student' },
    weeks: [
      ['Pengantar Basis Data', 'Konsep data, DBMS, dan arsitektur tiga level.'],
      ['Model Entity-Relationship', 'Entitas, atribut, relasi, dan kardinalitas.'],
      ['Normalisasi', 'Bentuk normal 1NF hingga BCNF.'],
      ['SQL Dasar', 'SELECT, INSERT, UPDATE, DELETE, dan JOIN.'],
    ],
  },
];

// ---- Bangun isi course seperti core_course_get_contents.
let cmSeq = 100;
const PAGES = [];
const ASSIGNS = [];
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
      ASSIGNS.push({ id: a.instance, cmid: a.id, course: c.id, name: a.name, intro: a.description, duedate: due, allowsubmissionsfromdate: start + (n - 1) * 7 * DAY, grade: 100, cutoffdate: 0 });
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
    return { courses: [{ ...courseSummary(c, user.id), categoryname: c.category, contacts }], warnings: [] };
  },
  core_course_get_contents(user, { courseid }) {
    const c = COURSE_DEFS.find((x) => x.id === Number(courseid));
    if (!c?.enrol[user.id]) return wsError('requireloginerror', 'Course or activity not accessible. (Not enrolled)');
    return CONTENTS[c.id].map((s) => ({ ...s, modules: s.modules.map(({ _course, _section, ...m }) => m) }));
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
    return {
      lastattempt: {
        submission: { status: g != null ? 'submitted' : 'new', timemodified: g != null ? a.duedate - DAY : 0 },
        gradingstatus: g != null ? 'graded' : 'notgraded',
        caneditowner: a.duedate > now(),
      },
      feedback: g != null ? { gradefordisplay: `${g.toFixed(2)} / 100.00` } : undefined,
      warnings: [],
    };
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

export async function mockRequestToken(username, password) {
  await sleep(200);
  const user = Object.values(USERS).find((u) => u.username === username);
  if (!user || password !== `${username}123`) {
    const { MoodleError } = await import('./moodleClient');
    throw new MoodleError('invalidlogin', 'Invalid login, please try again');
  }
  const token = `mock-${user.id}-${Date.now()}`;
  tokens.set(token, user.id);
  return token;
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
