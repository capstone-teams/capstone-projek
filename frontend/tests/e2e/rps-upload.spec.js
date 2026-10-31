import { test, expect } from '@playwright/test';

// FE-08.1: unggah RPS di kartu "1. RPS mata kuliah" tab Generator AI (mock backend).
async function seed(page) {
  await page.addInitScript(() => {
    localStorage.setItem('agentic-lms.moodle-session', JSON.stringify({ token: 'mock-3-test' }));
    localStorage.setItem('agentic-lms.token', 'mock-token:user_001');
  });
}
const pdf = (name, size = 2048) => ({ name, mimeType: 'application/pdf', buffer: Buffer.alloc(size, 'a') });

for (const width of [375, 1440]) {
  test(`lecturer validates, uploads, and processes an RPS at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await seed(page);
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    // Basis Data (kursus 3) belum punya project generator.
    await page.goto('/course/3/ai');
    await expect(page.getByRole('heading', { name: '1. RPS mata kuliah', exact: true })).toBeVisible();
    const input = page.locator('form.upload input[type="file"]');
    const submit = page.getByRole('button', { name: 'Unggah & proses' });

    // Ditolak sebelum dikirim: format dan ukuran.
    await input.setInputFiles({ name: 'catatan.txt', mimeType: 'text/plain', buffer: Buffer.from('x') });
    await expect(page.getByRole('alert')).toHaveText('Format file harus PDF atau DOCX.');
    await expect(submit).toBeDisabled();
    await input.setInputFiles(pdf('rps-besar.pdf', 21 * 1024 * 1024));
    await expect(page.getByRole('alert')).toHaveText('Ukuran file 21.0 MB melebihi batas 20.0 MB.');
    await expect(submit).toBeDisabled();

    // File valid: unggah, tampil di daftar, lalu selesai diproses.
    await input.setInputFiles(pdf('RPS-Basis-Data.pdf'));
    await expect(page.getByRole('alert')).toHaveCount(0);
    await submit.click();
    const row = page.getByRole('list', { name: 'Daftar RPS' }).getByRole('listitem').filter({ hasText: 'RPS-Basis-Data.pdf' });
    await expect(row).toBeVisible();
    await expect(row.getByText('Baru', { exact: true })).toBeVisible();
    await expect(row.getByText('Selesai dianalisis', { exact: true })).toBeVisible({ timeout: 15000 });
    await expect(page.getByLabel(/^RPS untuk kursus ini/)).toHaveValue(/.+/);
    await expect(page.getByLabel(/^RPS untuk kursus ini/).locator('option').first()).toHaveText('RPS-Basis-Data.pdf');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(errors).toEqual([]);
  });
}

test('FE-08.2: failed analysis shows its message and can be reanalyzed from the UI', async ({ page }) => {
  await seed(page);
  await page.goto('/course/3/ai');
  await page.locator('form.upload input[type="file"]').setInputFiles(pdf('rps-gagal-analisis.pdf'));
  await page.getByRole('button', { name: 'Unggah & proses' }).click();
  const row = page.getByRole('list', { name: 'Daftar RPS' }).getByRole('listitem').filter({ hasText: 'rps-gagal-analisis.pdf' });
  await expect(row.getByText('Gagal', { exact: true })).toBeVisible({ timeout: 15000 });
  await expect(row.getByText('Analisis RPS gagal. Coba analisis ulang.')).toBeVisible();
  await row.getByRole('button', { name: 'Analisis ulang' }).click();
  await expect(row.getByText('Selesai dianalisis', { exact: true })).toBeVisible({ timeout: 15000 });
  await row.getByRole('button', { name: 'Lihat hasil analisis' }).click();
  await expect(row.getByLabel('Ringkasan hasil analisis')).toContainText('16 minggu');
});
