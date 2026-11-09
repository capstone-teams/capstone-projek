import { useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';

/** { course, sections, isTeacher, canEdit, editMode, reload, setTrail } dari MoodleCourseLayout. */
export function useMoodleCourse() {
  return useOutletContext();
}

/**
 * Lanjutan breadcrumb kursus untuk halaman di dalamnya: [{ label, to? }], mis. section lalu aktivitas.
 * Breadcrumb utuh ("Kursus saya / <kursus> / ...") dirender sekali oleh MoodleCourseLayout di atas judul.
 */
export function useCourseBreadcrumb(trail) {
  const { setTrail } = useOutletContext() ?? {};
  const key = JSON.stringify(trail);
  useEffect(() => {
    if (!setTrail) return undefined;
    setTrail(JSON.parse(key));
    return () => setTrail([]);
  }, [setTrail, key]);
}
