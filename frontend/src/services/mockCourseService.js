import {
  DOSEN_COURSES,
  MAHASISWA_COURSES,
  RPS_ANALYSIS_DATA,
  WEEKLY_MATERIALS_DATA,
  WEEKS_DATA,
} from '../data/courseData.ts'

/** @type {import('./courseService.js').CourseService} */
export const mockCourseService = {
  async listInstructorCourses() {
    return structuredClone(DOSEN_COURSES)
  },
  async listStudentCourses() {
    return structuredClone(MAHASISWA_COURSES)
  },
  async listSyllabusWeeks() {
    return structuredClone(WEEKS_DATA)
  },
  async getRpsAnalysis() {
    return structuredClone(RPS_ANALYSIS_DATA)
  },
  async getMaterial(documentId, weekNumber) {
    const material = WEEKLY_MATERIALS_DATA[documentId]
      ?? WEEKLY_MATERIALS_DATA[weekNumber === 2 ? 'doc-week2-pdf' : 'doc-week3-pdf']
    return structuredClone(material)
  },
}
