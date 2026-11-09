import { api } from './apiClient';

export function getInstructorSetup() {
  return api.get('/instructors/me/setup');
}

export function updateInstructorSetup(setup) {
  return api.put('/instructors/me/setup', setup);
}

// Aliases for backward compatibility
export const getProfile = getInstructorSetup;
export const updateProfile = updateInstructorSetup;
