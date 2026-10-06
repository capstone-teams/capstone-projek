import { test, expect } from '@playwright/test';

export async function seedSession(page, role = 'dosen') {
  await page.addInitScript(({ role }) => {
    localStorage.setItem('agentic-lms.moodle-session', JSON.stringify({ token: role === 'dosen' ? 'mock-3-test' : 'mock-5-test' }));
    if (role === 'dosen') localStorage.setItem('agentic-lms.token', 'mock-token:user_001');
  }, { role });
}

test('anonymous access requires Moodle login and reaches Rakha dashboard', async ({ page }) => {
  await page.goto('/course/2/participants');
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('Username', { exact: true }).fill('dosen');
  await page.getByLabel('Kata sandi', { exact: true }).fill('dosen123');
  await page.getByRole('button', { name: 'Masuk', exact: true }).click();
  await expect(page).toHaveURL(/\/my$/);
  await expect(page.getByText('Kursus yang Anda ajar', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Menu pengguna' }).click();
  await page.getByRole('menuitem', { name: 'Kursus saya', exact: true }).click();
  await expect(page).toHaveURL(/\/my\/courses$/);
});

test('Moodle rejects the wrong password and preserves the login view', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Username', { exact: true }).fill('dosen');
  await page.getByLabel('Kata sandi', { exact: true }).fill('keliru');
  await page.getByRole('button', { name: 'Masuk', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Username atau password salah');
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => localStorage.getItem('agentic-lms.moodle-session'))).toBeNull();
});

test('mobile login controls and password recovery keep navigation usable', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('/login');
  const password = page.getByLabel('Kata sandi', { exact: true });
  await expect(password).toHaveAttribute('type', 'password');
  await page.getByRole('button', { name: 'Tampilkan kata sandi', exact: true }).click();
  await expect(password).toHaveAttribute('type', 'text');
  await page.getByRole('button', { name: 'Sembunyikan kata sandi', exact: true }).click();
  await expect(password).toHaveAttribute('type', 'password');

  await page.getByRole('button', { name: 'Lanjutkan dengan Google' }).click();
  await expect(page.getByRole('status')).toContainText('Login menggunakan Google belum tersedia');
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => localStorage.getItem('agentic-lms.moodle-session'))).toBeNull();

  await page.getByRole('link', { name: 'Lupa password?', exact: true }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);
  await page.getByLabel('Username atau alamat email', { exact: true }).fill('dosen');
  await page.getByRole('button', { name: 'Kirim instruksi pemulihan' }).click();
  await expect(page.getByRole('status')).toContainText('Pemulihan kata sandi belum tersedia');
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
  await page.getByRole('link', { name: 'Kembali ke halaman masuk' }).click();
  await expect(page.getByRole('heading', { name: 'Masuk ke akun Anda' })).toBeVisible();
});

const teacherPages = [
  ['/my', 'Kursus yang Anda ajar'],
  ['/my/courses', 'Basis Data'],
  ['/user/profile', 'Detail kursus'],
  ['/course/2', 'Minggu 1: Pengantar Pemrograman Web'],
  ['/course/2/participants', 'Andi Saputra'],
  ['/course/2/grades', 'Rekap nilai mahasiswa'],
  ['/course/2/mod/102', 'Konsep utama'],
  ['/ai', 'Generation project'],
  ['/ai/rps', 'RPS-Pemrograman-Web-2026.pdf'],
  ['/ai/courses/course_project_001/plan', 'Rencana course · versi 1'],
  ['/ai/courses/course_project_001/content', 'Tujuan pembelajaran'],
];
for (const [route, content] of teacherPages) {
  test('Rakha teacher route: ' + route, async ({ page }) => {
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await seedSession(page);
    await page.goto(route);
    await expect(page.getByText(content, { exact: false }).last()).toBeVisible();
    await expect(page.getByRole('navigation', { name: 'Navigasi utama', exact: true })).toHaveCount(0);
    await expect(page.locator('aside')).toHaveCount(0);
    expect(errors).toEqual([]);
  });
}

test('student sees Moodle data and is denied AI pages', async ({ page }) => {
  await seedSession(page, 'mahasiswa');
  await page.goto('/my');
  await expect(page.getByText('Ringkasan belajar', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Menu pengguna' }).click();
  await expect(page.getByRole('menuitem', { name: 'Generator AI' })).toHaveCount(0);
  await page.goto('/ai');
  await expect(page.getByRole('heading', { name: 'Khusus dosen' })).toBeVisible();
});

test('logout removes both Moodle and backend sessions and guards browser history', async ({ page }) => {
  // Seed once through an actual login: addInitScript would reseed on navigation.
  await page.goto('/login');
  await page.getByLabel('Username', { exact: true }).fill('dosen');
  await page.getByLabel('Kata sandi', { exact: true }).fill('dosen123');
  await page.getByRole('button', { name: 'Masuk', exact: true }).click();
  await expect(page).toHaveURL(/\/my$/);
  await expect.poll(() => page.evaluate(() => localStorage.getItem('agentic-lms.token'))).toBeTruthy();
  await page.getByRole('button', { name: 'Menu pengguna' }).click();
  await page.getByRole('menuitem', { name: 'Kursus saya', exact: true }).click();
  await expect(page).toHaveURL(/\/my\/courses$/);
  await page.getByRole('button', { name: 'Menu pengguna' }).click();
  await page.getByRole('menuitem', { name: 'Keluar' }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => [localStorage.getItem('agentic-lms.token'), localStorage.getItem('agentic-lms.moodle-session')])).toEqual([null, null]);
  await page.goBack();
  await expect(page.getByRole('heading', { name: 'Masuk ke akun Anda' })).toBeVisible();
});

test('plan approval and generation use Rakha workflow services', async ({ page }) => {
  test.setTimeout(60000);
  await seedSession(page);
  await page.goto('/ai/courses/course_project_002/plan');
  await page.getByRole('button', { name: 'Setujui rencana', exact: true }).click();
  await expect(page.getByText('Disetujui', { exact: true })).toBeVisible();
  // Client navigation keeps the shared mock backend in memory.
  await page.getByRole('link', { name: 'Konten', exact: true }).click();
  await page.getByRole('button', { name: 'Generate semua minggu', exact: true }).click();
  await expect(page.getByText('Tujuan pembelajaran', { exact: true })).toBeVisible({ timeout: 30000 });
  await page.getByRole('link', { name: 'Review', exact: true }).click();
  await page.getByRole('button', { name: 'Setujui semua konten', exact: true }).click();
  await page.getByRole('link', { name: 'Moodle', exact: true }).click();
  await page.getByRole('button', { name: 'Kirim ke Moodle', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: 'Ya, kirim', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Mulai verifikasi', exact: true })).toBeVisible({ timeout: 30000 });
  await page.getByRole('button', { name: 'Mulai verifikasi', exact: true }).click();
  await expect(page.getByText('passed', { exact: true })).toBeVisible({ timeout: 15000 });
});

test('unknown paths do not silently become an old mockup page', async ({ page }) => {
  await seedSession(page);
  await page.goto('/dashboard');
  await expect(page.getByRole('heading', { name: 'Halaman tidak ditemukan' })).toBeVisible();
});
