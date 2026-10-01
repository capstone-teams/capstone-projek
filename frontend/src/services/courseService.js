/**
 * UI-facing contract. A real API adapter can replace the mock without changing pages.
 * @typedef {object} CourseService
 * @property {() => Promise<import('../types/course').DosenCourse[]>} listInstructorCourses
 * @property {() => Promise<import('../types/course').MahasiswaCourse[]>} listStudentCourses
 * @property {() => Promise<import('../types/course').SyllabusWeek[]>} listSyllabusWeeks
 * @property {() => Promise<import('../types/course').RpsAnalysisData>} getRpsAnalysis
 * @property {(documentId: string, weekNumber: number) => Promise<import('../types/course').MaterialDocument>} getMaterial
 */

export {}
