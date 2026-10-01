import type { AppPath, NavItem } from '../types/navigation.ts'
import { APP_ROUTES, ROLE_NAVIGATION } from '../types/navigation.ts'
import type { AuthUser, UserRole } from '../types/auth.ts'

export const LOGIN_PATH: AppPath = '/login'
export const UNAUTHORIZED_PATH: AppPath = '/unauthorized'
export const NOT_FOUND_PATH: AppPath = '/not-found'

export function isAppPath(path: string | null | undefined): path is AppPath {
  return !!path && Object.hasOwn(APP_ROUTES, path)
}

/**
 * Resolves any URL pathname into a valid AppPath.
 * Root/empty paths go to /login (the guard forwards logged-in users to their home),
 * and unknown paths go to /not-found.
 */
export function resolveAppPath(path: string | null | undefined): AppPath {
  if (isAppPath(path)) return path
  if (!path || path === '/') return LOGIN_PATH
  return NOT_FOUND_PATH
}

/**
 * Returns the roles allowed to open a path, or null when any visitor/role may open it.
 */
export function getAllowedRoles(path: AppPath): readonly UserRole[] | null {
  const roles = APP_ROUTES[path].roles
  return roles && roles.length > 0 ? roles : null
}

/**
 * Determines whether the user role is permitted to access a given route.
 */
export function isPathAllowedForRole(path: AppPath, role: UserRole): boolean {
  const roles = getAllowedRoles(path)
  return roles === null || roles.includes(role)
}

/**
 * Returns the default landing path for a given role.
 */
export function getDefaultPathForRole(role: UserRole): AppPath {
  return role === 'STUDENT' ? '/student/courses' : '/dashboard'
}

/**
 * Returns the primary navigation menu for a given role.
 */
export function getNavigationForRole(role: UserRole): readonly NavItem[] {
  return ROLE_NAVIGATION[role]
}

export type RouteDecision =
  | { kind: 'allow'; path: AppPath }
  | {
      kind: 'redirect'
      path: AppPath
      reason: 'unauthenticated' | 'unauthorized' | 'already-authenticated'
    }

/**
 * Protected route behavior: decides whether the current user may open a path,
 * or where they should be redirected instead.
 */
export function resolveRouteAccess(path: AppPath, user: AuthUser | null): RouteDecision {
  const route = APP_ROUTES[path]

  if (route.access === 'public') {
    return { kind: 'allow', path }
  }

  if (route.access === 'guest') {
    return user
      ? { kind: 'redirect', path: getDefaultPathForRole(user.role), reason: 'already-authenticated' }
      : { kind: 'allow', path }
  }

  if (!user) {
    return { kind: 'redirect', path: LOGIN_PATH, reason: 'unauthenticated' }
  }

  if (!isPathAllowedForRole(path, user.role)) {
    return { kind: 'redirect', path: UNAUTHORIZED_PATH, reason: 'unauthorized' }
  }

  return { kind: 'allow', path }
}

/**
 * Picks where to land after a successful login: the originally requested
 * protected path when the role may open it, otherwise the role's home.
 */
export function getPostLoginPath(user: AuthUser, requestedPath: AppPath | null): AppPath {
  if (
    requestedPath &&
    APP_ROUTES[requestedPath].access === 'authenticated' &&
    isPathAllowedForRole(requestedPath, user.role)
  ) {
    return requestedPath
  }
  return getDefaultPathForRole(user.role)
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
    case '/unauthorized':
      return [{ label: 'Akses Ditolak' }]
    case '/not-found':
      return [{ label: 'Halaman Tidak Ditemukan' }]
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

