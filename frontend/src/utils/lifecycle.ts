import type { CoursePlanStage, WeeklyContentStage } from '../types/course.ts'

export type CoursePlanAction = 'GENERATE' | 'APPROVE' | 'PUBLISH' | 'RESET' | 'REVISE'
export type WeeklyContentAction = 'GENERATE' | 'SYNC' | 'RESET' | 'REVISE'

/**
 * Validates if a direct transition between two CoursePlan stages is legitimate.
 */
export function isValidCoursePlanTransition(
  from: CoursePlanStage,
  to: CoursePlanStage
): boolean {
  if (from === to) return true
  if (to === 'empty') return true // Reset is always allowed
  switch (from) {
    case 'empty':
      return to === 'review'
    case 'review':
      return to === 'approved'
    case 'approved':
      return to === 'published'
    case 'published':
      return false
    default:
      return false
  }
}

/**
 * Pure state machine transition function for Course Plan lifecycle.
 * Throws an Error if an illegal transition is attempted.
 */
export function transitionCoursePlanStage(
  current: CoursePlanStage,
  action: CoursePlanAction
): CoursePlanStage {
  switch (action) {
    case 'RESET':
      return 'empty'
    case 'GENERATE':
      if (current !== 'empty') {
        throw new Error(`Cannot generate course plan from stage '${current}'`)
      }
      return 'review'
    case 'REVISE':
      if (current !== 'review') {
        throw new Error(`Cannot request revision outside of 'review' stage, currently '${current}'`)
      }
      return 'review'
    case 'APPROVE':
      if (current !== 'review') {
        throw new Error(`Cannot approve course plan from stage '${current}', must be in 'review'`)
      }
      return 'approved'
    case 'PUBLISH':
      if (current !== 'approved') {
        throw new Error(`Cannot publish course plan from stage '${current}', must be in 'approved'`)
      }
      return 'published'
    default:
      return current
  }
}

/**
 * Validates if a direct transition between two Weekly Content stages is legitimate.
 */
export function isValidWeeklyContentTransition(
  from: WeeklyContentStage,
  to: WeeklyContentStage
): boolean {
  if (from === to) return true
  if (to === 'empty') return true // Reset is always allowed
  switch (from) {
    case 'empty':
      return to === 'review'
    case 'review':
      return to === 'synced'
    case 'synced':
      return false
    default:
      return false
  }
}

/**
 * Pure state machine transition function for Weekly Content lifecycle.
 * Throws an Error if an illegal transition is attempted.
 */
export function transitionWeeklyContentStage(
  current: WeeklyContentStage,
  action: WeeklyContentAction
): WeeklyContentStage {
  switch (action) {
    case 'RESET':
      return 'empty'
    case 'GENERATE':
      if (current !== 'empty') {
        throw new Error(`Cannot generate content from stage '${current}'`)
      }
      return 'review'
    case 'REVISE':
      if (current !== 'review') {
        throw new Error(`Cannot request revision outside of 'review' stage, currently '${current}'`)
      }
      return 'review'
    case 'SYNC':
      if (current !== 'review') {
        throw new Error(`Cannot sync content from stage '${current}', must be in 'review'`)
      }
      return 'synced'
    default:
      return current
  }
}
