import { test, expect } from '@playwright/test';

// FE-06.3: role dari GET /auth/me menentukan halaman awal, menu, dan akses halaman dosen.
async function login(page, username, password) {
  await page.goto('/login');
  await page.getByLabel('Username', { exact: true }).fill(username);
  await page.getByLabel('Kata sandi', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Masuk', exact: true }).click();
}
const siteNav = (page) => page.getByRole('navigation', { name: 'Navigasi situs' });

test('lecturer login opens the lecturer dashboard', async ({ page }) => {
  await login(page, 'dosen.demo', 'dosen.demo123');
  await expect(page).toHaveURL(/\/my$/);
  await expect(page.getByText('Kursus yang Anda ajar', { exact: true })).toBeVisible();
  await expect(siteNav(page).getByRole('link')).toHaveText(['Dasbor', 'Kursusku']);
  await page.goto('/');
  await expect(page).toHaveURL(/\/my$/);
});

test('student login opens the course page and lecturer URLs show access denied', async ({ page }) => {
  await login(page, '11231023', '11231023123');
  await expect(page).toHaveURL(/\/my\/courses$/);
  await expect(page.getByRole('heading', { name: 'Kursus saya', exact: true })).toBeVisible();
  await expect(siteNav(page).getByRole('link')).toHaveText(['Kursusku']);

  // Navigasi client (tanpa reload) agar sesi login tetap di memori mock.
  for (const route of ['/my', '/course/2/ai', '/course/2/ai/rps', '/course/2/ai/plan']) {
    await page.evaluate((path) => { window.history.pushState({}, '', path); window.dispatchEvent(new PopStateEvent('popstate')); }, route);
    await expect(page.getByRole('heading', { name: 'Akses ditolak' })).toBeVisible();
    await expect(page.getByText('sebagai mahasiswa', { exact: false })).toBeVisible();
  }
  await page.getByRole('link', { name: 'Ke halaman utama' }).click();
  await expect(page).toHaveURL(/\/my\/courses$/);
  await page.goto('/');
  await expect(page).toHaveURL(/\/my\/courses$/);
});
