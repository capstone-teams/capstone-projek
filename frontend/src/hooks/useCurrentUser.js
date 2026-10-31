import { useMemo } from 'react';
import { useAuth } from './useAuth';
import { ROLE } from '../types/auth';

/** Data user login beserta turunan peran yang sering dipakai halaman. */
export function useCurrentUser() {
  const { user, site } = useAuth();
  return useMemo(() => {
    const teacherIds = new Set(user?.teacherCourseIds ?? []);
    return {
      user,
      site,
      role: user?.role ?? null,
      isDosen: user?.role === ROLE.DOSEN,
      isMahasiswa: user?.role === ROLE.MAHASISWA,
      isTeacherOf: (courseId) => teacherIds.has(Number(courseId)),
    };
  }, [user, site]);
}
