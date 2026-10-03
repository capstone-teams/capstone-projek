import type { CourseService } from './courseService.ts'
import { mockCourseService } from './mockCourseService.ts'

// Change only this binding when the Backend API adapter is available.
export const courseService: CourseService = mockCourseService
