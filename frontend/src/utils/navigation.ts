import type { AppPath } from '../types/navigation.ts'
import { APP_ROUTES } from '../types/navigation.ts'
import type { UserRole } from '../types/auth.ts'

/**
 * Resolves any URL pathname into a valid AppPath, falling back to /dashboard for unknown routes.
 */
export function resolveAppPath(path: string | null | undefined): AppPath {
  if (path && path in APP_ROUTES) {
    return path as AppPath
  }
  return '/dashboard'
}

/**
 * Returns the target role associated with a path.
 */
export function getRoleForPath(path: AppPath): UserRole | 'public' {
  const route = APP_ROUTES[path]
  return route ? route.role : 'dosen'
}

/**
 * Determines whether the user role is permitted to access a given route.
 */
export function isPathAllowedForRole(path: AppPath, role: UserRole): boolean {
  const routeRole = getRoleForPath(path)
  if (routeRole === 'public') return true
  return routeRole === role
}

/**
 * Returns the default landing path for a given persona role.
 */
export function getDefaultPathForRole(role: UserRole): AppPath {
  return role === 'mahasiswa' ? '/student/courses' : '/dashboard'
}

export interface BreadcrumbItem {
  label: string
  path?: AppPath
}

/**
 * Returns the canonical breadcrumb hierarchy trail for any application route.
 */
export function getBreadcrumbTrail(path: AppPath): BreadcrumbItem[] {
  switch (path) {
    case '/login':
      return [{ label: 'Masuk' }]
    case '/dashboard':
      return [{ label: 'Dashboard' }]
    case '/course-plan':
      return [
        { label: 'Dashboard', path: '/dashboard' },
        { label: 'Aljabar Linear dan Geometri' },
      ]
    case '/rps-analysis':
      return [
        { label: 'Dashboard', path: '/dashboard' },
        { label: 'Aljabar Linear dan Geometri', path: '/course-plan' },
        { label: 'Hasil Analisis RPS' },
      ]
    case '/weekly-content':
      return [
        { label: 'Dashboard', path: '/dashboard' },
        { label: 'Aljabar Linear dan Geometri', path: '/course-plan' },
        { label: 'Detail Konten Mingguan' },
      ]
    case '/material-view':
      return [
        { label: 'Dashboard', path: '/dashboard' },
        { label: 'Aljabar Linear dan Geometri', path: '/course-plan' },
        { label: 'Detail Konten Mingguan', path: '/weekly-content' },
        { label: 'Penampil Dokumen Materi' },
      ]
    case '/student/courses':
      return [{ label: 'Mata Kuliah' }]
    case '/student/course':
      return [
        { label: 'Mata Kuliah', path: '/student/courses' },
        { label: 'Aljabar Linear dan Geometri' },
      ]
    case '/student/week':
      return [
        { label: 'Mata Kuliah', path: '/student/courses' },
        { label: 'Aljabar Linear dan Geometri', path: '/student/course' },
        { label: 'Minggu 03' },
      ]
    default:
      return [{ label: 'Beranda', path: '/dashboard' }]
  }
}

