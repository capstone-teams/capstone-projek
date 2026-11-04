import { test, expect } from '@playwright/test';

// FE-08.3: halaman Hasil Analisis RPS (tab RPS Generator AI) untuk RPS contoh (mock).
async function seed(page) {
  await page.addInitScript(() => {
    localStorage.setItem('agentic-lms.moodle-session', JSON.stringify({ token: 'mock-3-test' }));
    localStorage.setItem('agentic-lms.token', 'mock-token:user_001');
  });
}

for (const width of [375, 1440]) {
  test(`analysis result shows every section of the sample RPS at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await seed(page);
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto('/course/2/ai/rps');
    await expect(page.getByRole('heading', { name: 'Hasil analisis RPS' })).toBeVisible();
    for (const [title, status] of [
      ['Identitas mata kuliah', 'Belum lengkap'],
      ['CPL', 'Lengkap'],
      ['CPMK', 'Lengkap'],
      ['Sub-CPMK', 'Belum lengkap'],
      ['Rencana mingguan', 'Belum lengkap'],
      ['Penilaian', 'Lengkap'],
      ['Referensi', 'Lengkap'],
    ]) {
      await expect(page.getByRole('region', { name: `${title}: ${status}` })).toBeAttached();
    }
    const weeks = width < 1024
      ? page.getByRole('list', { name: 'Rencana mingguan RPS' }).getByRole('listitem')
      : page.getByRole('region', { name: 'Tabel rencana mingguan RPS' }).locator('tbody tr');
    await expect(weeks).toHaveCount(16);
    await expect(page.getByText('Catatan dari proses ekstraksi')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

    await page.getByRole('link', { name: 'Lanjut ke Course Planning' }).click();
    await expect(page).toHaveURL(/\/course\/2\/ai\/plan$/);
    expect(errors).toEqual([]);
  });
}
