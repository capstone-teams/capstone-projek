import { APP_ROUTES } from '../types/navigation.js';
/**
 * Returns the semantic path when registered, or null for an unknown route.
 */
export function resolveAppPath(path) {
    if (path && path in APP_ROUTES) {
        return path;
    }
    return null;
}
/**
 * Returns the target role associated with a path.
 */
export function getRoleForPath(path) {
    const route = APP_ROUTES[path];
    return route ? route.role : null;
}
/**
 * Determines whether the user role is permitted to access a given route.
 */
export function isPathAllowedForRole(path, role) {
    if (!(path in APP_ROUTES)) return false;
    const routeRole = getRoleForPath(path);
    if (routeRole === 'public')
        return true;
    if (routeRole === 'authenticated') return role === 'dosen' || role === 'mahasiswa';
    return routeRole === role;
}
/**
 * Returns the default landing path for a given persona role.
 */
export function getDefaultPathForRole(role) {
    return role === 'mahasiswa' ? '/student/courses' : '/dashboard';
}
/**
 * Returns the canonical breadcrumb hierarchy trail for any application route.
 */
export function getBreadcrumbTrail(path) {
    switch (path) {
        case '/login':
            return [{ label: 'Masuk' }];
        case '/dashboard':
            return [{ label: 'Dashboard' }];
        case '/course-plan':
            return [
                { label: 'Dashboard', path: '/dashboard' },
                { label: 'Aljabar Linear dan Geometri' },
            ];
        case '/rps-analysis':
            return [
                { label: 'Dashboard', path: '/dashboard' },
                { label: 'Aljabar Linear dan Geometri', path: '/course-plan' },
                { label: 'Hasil Analisis RPS' },
            ];
        case '/weekly-content':
            return [
                { label: 'Dashboard', path: '/dashboard' },
                { label: 'Aljabar Linear dan Geometri', path: '/course-plan' },
                { label: 'Detail Konten Mingguan' },
            ];
        case '/material-view':
            return [
                { label: 'Dashboard', path: '/dashboard' },
                { label: 'Aljabar Linear dan Geometri', path: '/course-plan' },
                { label: 'Detail Konten Mingguan', path: '/weekly-content' },
                { label: 'Penampil Dokumen Materi' },
            ];
        case '/student/courses':
            return [{ label: 'Mata Kuliah' }];
        case '/student/course':
            return [
                { label: 'Mata Kuliah', path: '/student/courses' },
                { label: 'Aljabar Linear dan Geometri' },
            ];
        case '/student/week':
            return [
                { label: 'Mata Kuliah', path: '/student/courses' },
                { label: 'Aljabar Linear dan Geometri', path: '/student/course' },
                { label: 'Minggu 03' },
            ];
        default:
            return [{ label: 'Beranda', path: '/dashboard' }];
    }
}
