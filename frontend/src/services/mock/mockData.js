// Data dummy untuk mode mock. Bentuk mengikuti contoh response di design-api.md.

// Akun sama dengan mock Moodle (mockMoodle.js); field mengikuti GET /auth/me backend.
// dosen.demo & 11231023 adalah akun uji backend (BE-06.3).
export const MOCK_USERS = [
  { id: 'user_001', username: 'dosen', firstname: 'Rina', lastname: 'Kartika', email: 'dosen@lecturer.itk.ac.id', role: 'INSTRUCTOR' },
  { id: 'user_002', username: 'mahasiswa', firstname: 'Andi', lastname: 'Saputra', email: 'mahasiswa@student.itk.ac.id', role: 'STUDENT' },
  { id: 'user_003', username: 'dosen2', firstname: 'Bayu', lastname: 'Pratama', email: 'dosen2@lecturer.itk.ac.id', role: 'INSTRUCTOR' },
  { id: 'user_004', username: 'mahasiswa2', firstname: 'Siti', lastname: 'Rahmawati', email: 'mahasiswa2@student.itk.ac.id', role: 'STUDENT' },
  { id: 'user_005', username: 'mahasiswa3', firstname: 'Dimas', lastname: 'Nugroho', email: 'mahasiswa3@student.itk.ac.id', role: 'STUDENT' },
  { id: 'user_006', username: 'dosen.demo', firstname: 'Dosen', lastname: 'Demo', email: 'dosen.demo@itk.ac.id', role: 'INSTRUCTOR' },
  { id: 'user_007', username: '11231023', firstname: 'Mahasiswa', lastname: 'Demo', email: '11231023@student.itk.ac.id', role: 'STUDENT' },
];

// Password mock sama dengan mock Moodle: "<username>123".
export const mockPassword = (username) => `${username}123`;

export const SAMPLE_TOPICS = [
  'Pengantar Pemrograman Web dan Arsitektur Client-Server',
  'HTML5: Struktur Dokumen dan Semantik',
  'CSS3: Selector, Box Model, dan Layout Flexbox/Grid',
  'JavaScript Dasar: Variabel, Fungsi, dan DOM',
  'JavaScript Lanjut: Event, Async, dan Fetch API',
  'Responsive Web Design dan Aksesibilitas',
  'Version Control dengan Git dan Kolaborasi Tim',
  'Ujian Tengah Semester',
  'HTTP, REST API, dan Format JSON',
  'Backend Dasar: Routing dan Controller',
  'Basis Data Relasional dan ORM',
  'Autentikasi dan Otorisasi Aplikasi Web',
  'Framework Frontend Berbasis Komponen',
  'Keamanan Aplikasi Web (OWASP Top 10)',
  'Deployment dan Proyek Akhir',
  'Ujian Akhir Semester',
];

export const EXAM_WEEKS = [8, 16];

export function buildRpsAnalysis(rpsId) {
  return {
    rps_id: rpsId,
    course: { name: 'Pemrograman Web', code: 'IF2105', credits: 3 },
    learning_outcomes: [
      { code: 'CPMK-1', description: 'Mahasiswa mampu menjelaskan arsitektur aplikasi web dan protokol HTTP.' },
      { code: 'CPMK-2', description: 'Mahasiswa mampu membangun antarmuka web yang responsif dan aksesibel.' },
      { code: 'CPMK-3', description: 'Mahasiswa mampu mengembangkan aplikasi web full-stack sederhana yang aman.' },
    ],
    topics: SAMPLE_TOPICS.filter((_, i) => !EXAM_WEEKS.includes(i + 1)),
    weekly_plan: SAMPLE_TOPICS.map((topic, i) => ({
      week: i + 1,
      topic,
      cpmk: i < 4 ? ['CPMK-1'] : i < 8 ? ['CPMK-2'] : ['CPMK-3'],
      method: EXAM_WEEKS.includes(i + 1) ? 'Ujian' : 'Ceramah, diskusi, praktikum',
    })),
    assessment: [
      { component: 'Tugas', weight: 30 },
      { component: 'Kuis', weight: 10 },
      { component: 'UTS', weight: 25 },
      { component: 'UAS', weight: 35 },
    ],
    references: [
      'Duckett, J. (2014). HTML and CSS: Design and Build Websites. Wiley.',
      'Haverbeke, M. (2018). Eloquent JavaScript (3rd ed.). No Starch Press.',
      'MDN Web Docs. https://developer.mozilla.org',
    ],
  };
}

export function buildPlanWeeks(instruction, analysis = buildRpsAnalysis()) {
  return SAMPLE_TOPICS.map((topic, i) => {
    const week = i + 1;
    const isExam = EXAM_WEEKS.includes(week);
    const rpsWeek = analysis.weekly_plan.find((item) => item.week === week);
    const subTopics = isExam ? [] : [`Konsep ${topic.split(':')[0]}`, 'Studi kasus', 'Latihan praktikum'];
    const objectives = isExam
      ? ['Mengevaluasi capaian pembelajaran']
      : [`Mahasiswa memahami ${topic.toLowerCase()}`, 'Mahasiswa mampu menerapkan konsep dalam praktikum'];
    return {
      week_number: week,
      title: topic,
      learning_outcomes: rpsWeek?.cpmk ?? [],
      objectives,
      topics: subTopics.length ? subTopics : [topic],
      teaching_methods: rpsWeek?.method ? rpsWeek.method.split(',').map((method) => method.trim()) : [],
      // Alias field digunakan pemilih minggu dan workflow konten.
      week,
      topic,
      sub_topics: subTopics,
      learning_objectives: objectives,
      planned_activities: isExam ? ['quiz'] : week % 2 === 0 ? ['learning_material', 'assignment'] : ['learning_material'],
      note: instruction && week >= 5 && week <= 8 ? `Disesuaikan: ${instruction}` : null,
    };
  });
}

export function buildWeekContent(week, topic, config, revision = 0) {
  const isExam = EXAM_WEEKS.includes(week);
  const suffix = revision > 0 ? ` (revisi ${revision})` : '';
  return {
    id: `content_w${String(week).padStart(2, '0')}`,
    week,
    topic,
    revision,
    learning_objectives: isExam
      ? ['Mengevaluasi capaian pembelajaran mahasiswa']
      : [`Menjelaskan konsep utama ${topic.toLowerCase()}`, 'Menerapkan konsep melalui latihan terarah'],
    materials:
      config.learning_material && !isExam
        ? [
            {
              id: `mat_w${week}_1`,
              title: `Materi Minggu ${week}: ${topic}${suffix}`,
              type: 'page',
              body_markdown:
                `## ${topic}\n\nPada pertemuan ini mahasiswa mempelajari ${topic.toLowerCase()}. ` +
                'Materi disusun berdasarkan RPS dan dilengkapi contoh kode serta latihan singkat.\n\n' +
                '### Ringkasan\n- Konsep dasar\n- Contoh penerapan\n- Kesalahan umum dan cara menghindarinya',
            },
          ]
        : [],
    resources: isExam ? [] : [{ title: 'MDN Web Docs', url: 'https://developer.mozilla.org' }],
    activities: {
      assignment:
        config.assignment && !isExam && week % 2 === 0
          ? {
              id: `asg_w${week}`,
              title: `Tugas Minggu ${week}${suffix}`,
              instructions: `Kerjakan studi kasus terkait ${topic.toLowerCase()} dan unggah laporan dalam format PDF.`,
              max_grade: 100,
            }
          : null,
      quiz:
        config.quiz && (isExam || week % 4 === 0)
          ? {
              id: `quiz_w${week}`,
              title: isExam ? topic : `Kuis Minggu ${week}`,
              questions: [
                {
                  question: `Pernyataan mana yang paling tepat terkait ${topic.toLowerCase()}?`,
                  options: ['Pilihan A', 'Pilihan B', 'Pilihan C', 'Pilihan D'],
                  answer: 0,
                },
              ],
            }
          : null,
    },
  };
}
