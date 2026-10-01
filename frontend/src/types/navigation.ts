import type { UserRole } from './auth.ts'

export type AppPath =
  | '/login'
  | '/dashboard'
  | '/rps-analysis'
  | '/course-plan'
  | '/weekly-content'
  | '/material-view'
  | '/student/courses'
  | '/student/course'
  | '/student/week'
  | '/unauthorized'
  | '/not-found'

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

/**
 * - `public`: dapat dibuka siapa saja (sudah login atau belum).
 * - `guest`: hanya untuk pengguna yang belum login (mis. halaman login).
 * - `authenticated`: wajib login; dibatasi lagi oleh `roles` bila diisi.
 */
export type RouteAccess = 'public' | 'guest' | 'authenticated'

export interface RouteMetadata {
  path: AppPath
  title: string
  access: RouteAccess
  /** Role yang boleh membuka route. Kosong berarti semua role yang sudah login. */
  roles?: readonly UserRole[]
}

export const APP_ROUTES: Record<AppPath, RouteMetadata> = {
  '/login': {
    path: '/login',
    title: 'Masuk — LMS ITK',
    access: 'guest',
  },
  '/dashboard': {
    path: '/dashboard',
    title: 'Dashboard Dosen — LMS ITK',
    access: 'authenticated',
    roles: ['INSTRUCTOR'],
  },
  '/rps-analysis': {
    path: '/rps-analysis',
    title: 'Hasil Analisis RPS — Aljabar Linear dan Geometri — LMS ITK',
    access: 'authenticated',
    roles: ['INSTRUCTOR'],
  },
  '/course-plan': {
    path: '/course-plan',
    title: 'Aljabar Linear dan Geometri (Course Plan) — LMS ITK',
    access: 'authenticated',
    roles: ['INSTRUCTOR'],
  },
  '/weekly-content': {
    path: '/weekly-content',
    title: 'Detail Konten Mingguan — LMS ITK',
    access: 'authenticated',
    roles: ['INSTRUCTOR'],
  },
  '/material-view': {
    path: '/material-view',
    title: 'Penampil Dokumen Materi — LMS ITK',
    access: 'authenticated',
  },
  '/student/courses': {
    path: '/student/courses',
    title: 'Matakuliah Saya — LMS ITK',
    access: 'authenticated',
    roles: ['STUDENT'],
  },
  '/student/course': {
    path: '/student/course',
    title: 'Silabus Matakuliah — LMS ITK',
    access: 'authenticated',
    roles: ['STUDENT'],
  },
  '/student/week': {
    path: '/student/week',
    title: 'Materi Kuliah Minggu 03 — LMS ITK',
    access: 'authenticated',
    roles: ['STUDENT'],
  },
  '/unauthorized': {
    path: '/unauthorized',
    title: 'Akses Ditolak — LMS ITK',
    access: 'public',
  },
  '/not-found': {
    path: '/not-found',
    title: 'Halaman Tidak Ditemukan — LMS ITK',
    access: 'public',
  },
}

export interface NavItem {
  label: string
  path: AppPath
}

/**
 * Menu navigasi utama untuk setiap role.
 */
export const ROLE_NAVIGATION: Record<UserRole, readonly NavItem[]> = {
  INSTRUCTOR: [
    { label: 'Dashboard', path: '/dashboard' },
    { label: 'Course Plan', path: '/course-plan' },
  ],
  STUDENT: [
    { label: 'Mata Kuliah', path: '/student/courses' },
    { label: 'Silabus', path: '/student/course' },
  ],
}
