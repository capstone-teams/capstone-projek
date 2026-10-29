import { test, expect } from '@playwright/test';

// FE-06.2: login, logout & session restore terhadap kontrak auth backend (mode mock).
// Akun uji BE-06.3; password mock = "<username>123".
const ACCOUNTS = [
  { label: 'instructor', username: 'dosen.demo', password: 'dosen.demo123', home: /\/my$/, landing: 'Kursus yang Anda ajar', name: 'Dosen Demo', aiMenu: 1 },
  { label: 'student', username: '11231023', password: '11231023123', home: /\/my\/courses$/, landing: 'Kursus saya', name: 'Mahasiswa Demo', aiMenu: 0 },
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
    // Halaman awal sesuai role (FE-06.3): dosen ke dashboard, mahasiswa ke halaman course.
    await expect(page).toHaveURL(account.home);
    await expect(page.getByText(account.landing, { exact: false }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Menu pengguna' })).toContainText(account.name);
    await page.getByRole('button', { name: 'Menu pengguna' }).click();
    await page.getByRole('menuitem', { name: 'Kursus saya', exact: true }).click();
    await expect(page).toHaveURL(/\/my\/courses$/);
    const before = await tokens(page);
    expect(before[0]).toBeTruthy();
    expect(before[1]).toBeTruthy();

    // Reload memulihkan sesi lewat GET /auth/me selama token masih berlaku.
    await page.reload();
    await expect(page).toHaveURL(/\/my\/courses$/);
    await expect(page.getByRole('button', { name: 'Menu pengguna' })).toContainText(account.name);
    expect(await tokens(page)).toEqual(before);
    // Role dari backend: hanya instructor yang melihat tab Generator AI di kursus yang diajarnya.
    await page.goto('/course/2');
    await expect(page.getByRole('link', { name: 'Peserta', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Generator AI', exact: true })).toHaveCount(account.aiMenu);
    await page.getByRole('button', { name: 'Menu pengguna' }).click();

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
