import { api } from './apiClient';

// Monitoring workflow dan course target (design-api §16, BE-11.3).

export function listWorkflows() {
  return api.get('/workflows').then((data) => data.items);
}

export function getWorkflow(workflowId) {
  return api.get(`/workflows/${workflowId}`);
}

export function getWorkflowEvents(workflowId) {
  return api.get(`/workflows/${workflowId}/events`).then((data) => data.items);
}

/** PUT /workflows/{id}/moodle-target: id kursus memilih target, null melepaskannya. */
export function setMoodleTarget(workflowId, moodleCourseId) {
  return api.put(`/workflows/${workflowId}/moodle-target`, { moodle_course_id: moodleCourseId });
}

/** Workflow yang menargetkan kursus ini. Daftar tidak memuat moodle_course_id, jadi detailnya dibaca. */
export async function findWorkflowForCourse(moodleCourseId) {
  const workflows = await Promise.all((await listWorkflows()).map((item) => getWorkflow(item.id)));
  return workflows.find((workflow) => workflow.moodle_course_id === Number(moodleCourseId)) ?? null;
}
