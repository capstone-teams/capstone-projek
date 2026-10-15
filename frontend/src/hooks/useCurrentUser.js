import { useMemo } from 'react';
import { useAuth } from './useAuth';

/** Data user login beserta turunan peran yang sering dipakai halaman. */
export function useCurrentUser() {
  const { user, site } = useAuth();
  return useMemo(() => {
    const teacherIds = new Set(user?.teacherCourseIds ?? []);
    return {
      user,
      site,
      role: user?.role ?? null,
      isDosen: user?.role === 'dosen',
      isMahasiswa: user?.role === 'mahasiswa',
      isTeacherOf: (courseId) => teacherIds.has(Number(courseId)),
    };
  }, [user, site]);
}
