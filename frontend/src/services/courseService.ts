import type {
  DosenCourse,
  MahasiswaCourse,
  MaterialDocument,
  RpsAnalysisData,
  SyllabusWeek,
} from '../types/course'

/** UI-facing contract. A real API adapter can replace the mock without changing pages. */
export interface CourseService {
  listInstructorCourses(): Promise<DosenCourse[]>
  listStudentCourses(): Promise<MahasiswaCourse[]>
  listSyllabusWeeks(): Promise<SyllabusWeek[]>
  getRpsAnalysis(): Promise<RpsAnalysisData>
  getMaterial(documentId: string, weekNumber: number): Promise<MaterialDocument>
}
