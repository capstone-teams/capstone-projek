import { api, idempotencyHeader } from './apiClient';
import { normalizeCoursePlan } from './coursePlanAdapter';

export function listCourses() {
  return api.get('/courses');
}

/**
 * Mencari project generator milik kursus Moodle.
 */
export async function findCourseByMoodleId(moodleCourseId) {
  const res = await api.get('/courses', { query: { moodle_course_id: moodleCourseId } }).catch(() => null);
  const list = res?.items ?? res?.courses ?? [];
  const found = list.find((c) => String(c.moodle_course_id) === String(moodleCourseId) || String(c.id) === String(moodleCourseId));
  const targetId = found?.id ?? moodleCourseId;
  const detail = await api.get(`/courses/${targetId}`).catch(() => null);
  return detail ?? found ?? null;
}

export function createCourse(payload) {
  return api.post('/courses', payload);
}

export function getCourse(courseId) {
  return api.get(`/courses/${courseId}`);
}

export function updateActivityConfiguration(courseId, config) {
  return api.put(`/courses/${courseId}/activity-configuration`, config);
}

// Course Planning

export function generatePlan(courseId) {
  return api.post(`/courses/${courseId}/plan`);
}

export function getPlan(courseId) {
  return api.get(`/courses/${courseId}/plan`).then(normalizeCoursePlan);
}

export function approvePlan(courseId) {
  return api.post(`/courses/${courseId}/plan/approve`);
}

export function regeneratePlan(courseId, instruction) {
  return api.post(`/courses/${courseId}/plan/regenerate`, { instruction });
}

// Content

export function generateContent(courseId, weeks = 'all') {
  return api.post(`/courses/${courseId}/content/generate`, { weeks }, { headers: idempotencyHeader() });
}

export function getContent(courseId, week) {
  return api.get(`/courses/${courseId}/content`, { query: { week } });
}

export function regenerateContent(courseId, contentId, instruction) {
  return api.post(
    `/courses/${courseId}/content/${contentId}/regenerate`,
    { instruction },
    { headers: idempotencyHeader() },
  );
}

// Validation

export function validateContent(courseId) {
  return api.post(`/courses/${courseId}/validation`);
}

export function getValidation(courseId) {
  return api.get(`/courses/${courseId}/validation`);
}

// Review

export function getReview(courseId) {
  return api.get(`/courses/${courseId}/review`).catch(() => ({ items: [] }));
}

export function approveContent(courseId) {
  return api.post(`/courses/${courseId}/review/approve`);
}

export function rejectContent(courseId, reason) {
  return api.post(`/courses/${courseId}/review/reject`, { reason });
}

// Moodle Execution

export function executeCourse(courseId) {
  return api.post(`/courses/${courseId}/execute`, undefined, { headers: idempotencyHeader() });
}

export function getExecution(courseId, executionId) {
  return api.get(`/courses/${courseId}/execution/${executionId}`);
}

export function cancelExecution(courseId, executionId) {
  return api.post(`/courses/${courseId}/execution/${executionId}/cancel`);
}

// Verification

export function startVerification(courseId) {
  return api.post(`/courses/${courseId}/verification`, undefined, { headers: idempotencyHeader() });
}

export function getVerification(courseId, verificationId) {
  return api.get(`/courses/${courseId}/verification/${verificationId}`);
}

// Agent Run & Monitoring

export function getAgentRun(runId) {
  return api.get(`/agent-runs/${runId}`);
}

export function getAgentRuns(courseId) {
  return api.get(`/courses/${courseId}/agent-runs`).catch(() => ({ runs: [] }));
}

export function getMonitoring(courseId) {
  return api.get(`/courses/${courseId}/monitoring`).catch(() => ({ recent_events: [] }));
}
