import { test, expect } from '@playwright/test';

// FE-06.2: login, logout & session restore terhadap kontrak auth backend (mode mock).
// Akun uji BE-06.3; password mock = "<username>123".
const ACCOUNTS = [
  { label: 'instructor', username: 'dosen.demo', password: 'dosen.demo123', landing: 'Kursus yang Anda ajar', name: 'Dosen Demo', aiMenu: 1 },
  { label: 'student', username: '11231023', password: '11231023123', landing: 'Ringkasan belajar', name: 'Mahasiswa Demo', aiMenu: 0 },
];
const tokens = (page) => page.evaluate(() => [localStorage.getItem('agentic-lms.token'), localStorage.getItem('agentic-lms.moodle-session')]);

async function login(page, username, password) {
  await page.getByLabel('Username', { exact: true }).fill(username);
  await page.getByLabel('Kata sandi', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Masuk', exact: true }).click();
}

for (const account of ACCOUNTS) {
  test(`${account.label} test account logs in, survives reload and logs out`, async ({ page }) => {
    await page.goto('/my/courses');
    await expect(page).toHaveURL(/\/login$/);
    await login(page, account.username, account.password);
    await expect(page).toHaveURL(/\/my\/courses$/);
    await expect(page.getByRole('button', { name: 'Menu pengguna' })).toContainText(account.name);
    const before = await tokens(page);
    expect(before[0]).toBeTruthy();
    expect(before[1]).toBeTruthy();

    // Reload memulihkan sesi lewat GET /auth/me selama token masih berlaku.
    await page.reload();
    await expect(page).toHaveURL(/\/my\/courses$/);
    await expect(page.getByRole('button', { name: 'Menu pengguna' })).toContainText(account.name);
    expect(await tokens(page)).toEqual(before);
    await page.goto('/my');
    await expect(page.getByText(account.landing, { exact: false }).first()).toBeVisible();
    await page.getByRole('button', { name: 'Menu pengguna' }).click();
    await expect(page.getByRole('menuitem', { name: 'Generator AI' })).toHaveCount(account.aiMenu);

    // Logout menghapus token & user; halaman terproteksi tidak dapat diakses lagi.
    await page.getByRole('menuitem', { name: 'Keluar' }).click();
    await expect(page).toHaveURL(/\/login$/);
    expect(await tokens(page)).toEqual([null, null]);
    for (const route of ['/my', '/my/courses', '/course/2']) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login$/);
      await expect(page.getByRole('heading', { name: 'Masuk ke akun Anda' })).toBeVisible();
    }
  });
}

test('login accepts the email identifier and shows the loading state', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Username', { exact: true }).fill('DOSEN.DEMO@itk.ac.id');
  await page.getByLabel('Kata sandi', { exact: true }).fill('dosen.demo123');
  const submit = page.getByRole('button', { name: 'Masuk', exact: true });
  await submit.click();
  await expect(page.getByRole('button', { name: 'Memproses…', exact: true })).toBeDisabled();
  await expect(page).toHaveURL(/\/my$/);
  await expect(page.getByRole('button', { name: 'Menu pengguna' })).toContainText('Dosen Demo');
});

test('wrong credentials show the backend error and keep the session empty', async ({ page }) => {
  await page.goto('/login');
  await login(page, 'dosen.demo', 'password-salah');
  const alert = page.getByRole('alert');
  await expect(alert).toContainText('Login gagal');
  await expect(alert).toContainText('Autentikasi gagal.');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('button', { name: 'Masuk', exact: true })).toBeEnabled();
  expect(await tokens(page)).toEqual([null, null]);
});
