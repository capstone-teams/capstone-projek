import { mockCourseService } from './mockCourseService.js'

// Change only this binding when the Backend API adapter is available.
/** @type {import('./courseService.js').CourseService} */
export const courseService = mockCourseService
