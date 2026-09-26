export type CoursePlanStage = 'empty' | 'review' | 'approved' | 'published'
export type WeeklyContentStage = 'empty' | 'review' | 'synced'

export type MaterialFileType = 'pdf' | 'ppt' | 'assignment'

export interface MaterialSection {
  heading: string
  content: string
  formula?: string
  diagramType?: 'matrix-operations' | 'matrix-determinant' | 'gauss-elimination'
}

export interface MaterialDocument {
  id: string
  weekNumber: number
  title: string
  fileType: MaterialFileType
  fileSize: string
  estimatedTime?: string
  uploadedDate: string
  description: string
  subCpmkRef: string
  sections: MaterialSection[]
  exercisePrompt?: string
}

export interface SyllabusWeek {
  weekNumber: number
  title: string
  duration: string
  status: 'draft' | 'approved' | 'moodle' | 'pending'
}

export interface DosenCourse {
  code: string
  name: string
  sks: string
  semester: string
  badge: string
  badgeType: 'draft' | 'approved' | 'moodle'
  progress: string
}

export interface MahasiswaCourse {
  code: string
  name: string
  dosen: string
  sks: string
  available: string
  badge: string
  badgeType: 'approved' | 'moodle'
}

export interface RpsWeekPlan {
  weekNumber: number
  subCpmk: string
  bahanKajian: string[]
}

export interface RpsAnalysisData {
  courseCode: string
  courseName: string
  sks: number
  semester: string
  totalWeeks: number
  programStudi?: string
  dosenPengampu?: string
  koordinatorProdi?: string
  tanggalPenyusunan?: string
  deskripsiSingkat?: string
  targetCpl: string[]
  cpmkList?: string[]
  cpmkCount: number
  fileName: string
  fileSize: string
  extractedAt: string
  weeklyPlans: RpsWeekPlan[]
}
