import { api } from './apiClient';

// design-api.md §7. Form memakai field datar; kontrak backend mengelompokkannya di instructor_profile.
const SETUP_PATH = '/instructors/me/setup';
const flatten = ({ instructor_profile: profile, ...setup }) => ({ ...profile, ...setup });

export function getProfile() {
  return api.get(SETUP_PATH).then(flatten);
}

export function updateProfile({ additional_prompt, activity_configuration, ...instructor_profile }) {
  return api.put(SETUP_PATH, { instructor_profile, additional_prompt, activity_configuration }).then(flatten);
}
