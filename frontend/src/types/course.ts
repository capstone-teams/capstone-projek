export type CoursePlanStage = 'empty' | 'review' | 'approved' | 'published'
export type WeeklyContentStage = 'empty' | 'review' | 'synced'

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

export interface RpsAnalysisData {
  courseCode: string
  courseName: string
  sks: number
  semester: string
  totalWeeks: number
  targetCpl: string[]
  cpmkCount: number
  fileName: string
  fileSize: string
  extractedAt: string
}
