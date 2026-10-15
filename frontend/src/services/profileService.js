import { api } from './apiClient';

// design-api.md §7

export function getProfile() {
  return api.get('/instructors/me/profile');
}

export function updateProfile(profile) {
  return api.put('/instructors/me/profile', profile);
}
