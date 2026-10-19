export const APP_ROUTES = {
    '/login': {
        path: '/login',
        title: 'Masuk — LMS ITK',
        role: 'public',
    },
    '/dashboard': {
        path: '/dashboard',
        title: 'Dashboard Dosen — LMS ITK',
        role: 'dosen',
    },
    '/rps-analysis': {
        path: '/rps-analysis',
        title: 'Hasil Analisis RPS — Aljabar Linear dan Geometri — LMS ITK',
        role: 'dosen',
    },
    '/course-plan': {
        path: '/course-plan',
        title: 'Aljabar Linear dan Geometri (Course Plan) — LMS ITK',
        role: 'dosen',
    },
    '/weekly-content': {
        path: '/weekly-content',
        title: 'Detail Konten Mingguan — LMS ITK',
        role: 'dosen',
    },
    '/material-view': {
        path: '/material-view',
        title: 'Penampil Dokumen Materi — LMS ITK',
        role: 'authenticated',
    },
    '/student/courses': {
        path: '/student/courses',
        title: 'Matakuliah Saya — LMS ITK',
        role: 'mahasiswa',
    },
    '/student/course': {
        path: '/student/course',
        title: 'Silabus Matakuliah — LMS ITK',
        role: 'mahasiswa',
    },
    '/student/week': {
        path: '/student/week',
        title: 'Materi Kuliah Minggu 03 — LMS ITK',
        role: 'mahasiswa',
    },
};
