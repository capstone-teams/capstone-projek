// Status autentikasi yang diekspos AuthProvider.
export const AUTH_STATUS = {
    INITIALIZING: 'initializing',
    AUTHENTICATED: 'authenticated',
    ANONYMOUS: 'anonymous',
};
// Alasan sesi berakhir tanpa logout eksplisit.
export const SESSION_NOTICE = {
    EXPIRED: 'expired',
    // Sesi belum dapat dipulihkan karena server tidak terjangkau; token tetap disimpan.
    UNAVAILABLE: 'unavailable',
};
// Role aplikasi mengikuti istilah proposal (DOSEN/MAHASISWA). Backend mengirim enum kanonik
// INSTRUCTOR/STUDENT/ADMIN dari GET /auth/me; padanannya satu-satu (auth-api-integration.md, BE-06.4).
export const ROLE = {
    DOSEN: 'DOSEN',
    MAHASISWA: 'MAHASISWA',
    ADMIN: 'ADMIN',
};
export const ROLE_FROM_BACKEND = {
    INSTRUCTOR: ROLE.DOSEN,
    STUDENT: ROLE.MAHASISWA,
    ADMIN: ROLE.ADMIN,
};
export const ROLE_LABEL = {
    [ROLE.DOSEN]: 'Dosen',
    [ROLE.MAHASISWA]: 'Mahasiswa',
    [ROLE.ADMIN]: 'Admin',
};
// Halaman awal setelah login (Proposal §3.3.1): dosen ke dashboard, mahasiswa ke halaman course.
export const HOME_PATH = {
    [ROLE.DOSEN]: '/my',
    [ROLE.MAHASISWA]: '/my/courses',
    [ROLE.ADMIN]: '/my/courses',
};
export function homePathFor(role) {
    return HOME_PATH[role] ?? '/my/courses';
}
