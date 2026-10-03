/** Restore a fixture session through the real AuthProvider /auth/me boundary. */
export async function openAs(page, path, role = path.startsWith('/student/') ? 'mahasiswa' : 'dosen') {
  await page.addInitScript(({ role, anonymous }) => {
    if (anonymous) localStorage.removeItem('agentic-lms.token');
    else localStorage.setItem('agentic-lms.token', `mock-token:${role === 'mahasiswa' ? 'user_002' : 'user_001'}`);
  }, { role, anonymous: path === '/login' });
  await page.goto(path);
}
