import { useMemo } from 'react';
import { useAuth } from './useAuth';
import { ROLE } from '../types/auth';

/** Data user login beserta turunan peran yang sering dipakai halaman. */
export function useCurrentUser() {
  const { user, site } = useAuth();
  return useMemo(() => {
    const teacherIds = new Set(user?.teacherCourseIds ?? []);
    const isDosen = user?.role === ROLE.DOSEN;
    return {
      user,
      site,
      role: user?.role ?? null,
      isDosen,
      isMahasiswa: user?.role === ROLE.MAHASISWA,
      // Tanpa data kursus ajar dari Moodle (Backend Gateway), dosen dianggap pengajar kursus yang dapat ia buka.
      isTeacherOf: (courseId) => (user?.teacherCourseIds ? teacherIds.has(Number(courseId)) : isDosen),
    };
  }, [user, site]);
}
