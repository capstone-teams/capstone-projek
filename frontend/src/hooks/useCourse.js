import { useOutletContext } from 'react-router-dom';

/** Akses { course, events, version, refresh } yang disediakan AiCourseLayout. */
export function useCourse() {
  return useOutletContext();
}
