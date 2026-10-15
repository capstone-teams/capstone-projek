import { useOutletContext } from 'react-router-dom';

/** { course, sections, isTeacher } dari MoodleCourseLayout. */
export function useMoodleCourse() {
  return useOutletContext();
}
