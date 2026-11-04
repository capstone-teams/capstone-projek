import { useOutletContext } from 'react-router-dom';

/** { course, sections, isTeacher, canEdit, editMode, reload } dari MoodleCourseLayout. */
export function useMoodleCourse() {
  return useOutletContext();
}
