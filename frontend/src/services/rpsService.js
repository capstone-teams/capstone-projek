import { api } from './apiClient';

// design-api.md §6

export const RPS_ACCEPTED_TYPES = '.pdf,.docx';
export const RPS_MAX_SIZE_MB = 10;

export function uploadRps(file) {
  const form = new FormData();
  form.append('file', file);
  return api.post('/rps', form);
}

export function listRps() {
  return api.get('/rps');
}

export function getRps(rpsId) {
  return api.get(`/rps/${rpsId}`);
}

export function processRps(rpsId) {
  return api.post(`/rps/${rpsId}/process`);
}

export function getRpsAnalysis(rpsId) {
  return api.get(`/rps/${rpsId}/analysis`);
}
