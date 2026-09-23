export type AppPath =
  | '/login'
  | '/dashboard'
  | '/rps-analysis'
  | '/course-plan'
  | '/weekly-content'
  | '/student/courses'
  | '/student/course'
  | '/student/week'

export type ModalType =
  | 'upload-rps'
  | 'rps-progress'
  | 'profile'
  | 'generate-plan'
  | 'plan-progress'
  | 'plan-revision'
  | 'generate-content'
  | 'content-progress'
  | 'content-revision'
  | 'moodle-publish'
  | 'moodle-sync'
  | null

export interface RouteMetadata {
  path: AppPath
  title: string
  role: 'dosen' | 'mahasiswa' | 'public'
}

export const APP_ROUTES: Record<AppPath, RouteMetadata> = {
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
    title: 'Hasil Analisis RPS — Keamanan Siber — LMS ITK',
    role: 'dosen',
  },
  '/course-plan': {
    path: '/course-plan',
    title: 'Keamanan Siber (Course Plan) — LMS ITK',
    role: 'dosen',
  },
  '/weekly-content': {
    path: '/weekly-content',
    title: 'Detail Konten Mingguan — LMS ITK',
    role: 'dosen',
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
}
