import { useOutletContext } from 'react-router-dom';

/** { course, sections, isTeacher } dari CourseLayout Moodle. */
export function useMoodleCourse() {
  return useOutletContext();
}
