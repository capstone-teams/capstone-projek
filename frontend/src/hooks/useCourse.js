import { useOutletContext } from 'react-router-dom';

/** Akses { course, events, version, refresh } yang disediakan CourseLayout. */
export function useCourse() {
  return useOutletContext();
}
