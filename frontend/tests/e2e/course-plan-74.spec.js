import { test, expect } from '@playwright/test';

async function seed(page) {
  await page.addInitScript(() => {
    localStorage.setItem('agentic-lms.moodle-session', JSON.stringify({ token: 'mock-3-test' }));
    localStorage.setItem('agentic-lms.token', 'mock-token:user_001');
  });
}

for (const width of [375, 768, 1024, 1440]) {
  test('course plan stays readable at ' + width + 'px', async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    await seed(page);
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto('/ai/courses/course_project_001/plan');
    await expect(page.getByRole('heading', { name: 'Rencana course · versi 1', exact: true })).toBeVisible();
    await expect(page.getByText('Disetujui', { exact: true })).toBeVisible();
    await expect(page.getByText('3 SKS', { exact: true })).toBeVisible();
    await expect(page.getByText('16 minggu', { exact: true })).toBeVisible();
    const weeks = width < 1024
      ? page.getByRole('list', { name: 'Rencana pembelajaran mingguan' }).getByRole('article')
      : page.getByRole('table', { name: 'Rencana pembelajaran mingguan' }).locator('tbody tr');
    await expect(weeks).toHaveCount(16);
    const first = weeks.first();
    for (const text of ['CPMK-1 — Mahasiswa mampu menjelaskan arsitektur aplikasi web dan protokol HTTP.', 'Mahasiswa mampu menerapkan konsep dalam praktikum', 'Ceramah', 'Materi']) {
      await expect(first.getByText(text, { exact: true })).toBeVisible();
    }
    if (width < 1024) {
      await expect(page.getByRole('table')).toHaveCount(0);
      for (const week of await weeks.all()) {
        const bounds = await week.boundingBox();
        expect(bounds.x).toBeGreaterThanOrEqual(0);
        expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
      }
      await expect(weeks.nth(7).getByText('Ujian', { exact: true })).toBeVisible();
    } else {
      await expect(page.getByRole('columnheader', { name: 'Capaian pembelajaran', exact: true })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'Metode mengajar', exact: true })).toBeVisible();
      const scroll = page.getByRole('region', { name: 'Tabel rencana mingguan' });
      const bounds = await scroll.boundingBox();
      expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await expect(page.locator('aside')).toHaveCount(0);
    expect(errors).toEqual([]);
    // Capture overview and the complete first week for a compact visual review.
    await page.evaluate(() => window.scrollTo(0, 0));
    const overview = testInfo.outputPath('course-plan-' + width + '.png');
    await page.screenshot({ path: overview });
    await testInfo.attach('course plan overview', { path: overview, contentType: 'image/png' });
    const detail = testInfo.outputPath('first-week-' + width + '.png');
    await first.screenshot({ path: detail });
    await testInfo.attach('first week detail', { path: detail, contentType: 'image/png' });
  });
}

test('a new course shows the empty plan then generates all schema fields', async ({ page }) => {
  await seed(page);
  await page.goto('/ai/courses/new');
  await page.getByRole('button', { name: 'Buat course', exact: true }).click();
  await expect(page).toHaveURL(/\/ai\/courses\/course_project_003$/);
  await page.getByRole('link', { name: 'Rencana', exact: true }).click();
  await expect(page.getByText('Rencana belum dibuat.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Generate rencana', exact: true }).click();
  await expect(page.getByText('Agent sedang menyusun rencana…', { exact: true })).toBeVisible();
  await expect(page.getByRole('table').locator('tbody tr')).toHaveCount(16);
  await expect(page.getByText('Draft', { exact: true })).toBeVisible();
  await expect(page.getByRole('table').locator('tbody tr').first()).toContainText('CPMK-1');
  await expect(page.getByRole('table').locator('tbody tr').first()).toContainText('Ceramah');
});

test('Rakha revision and approval keep the enriched plan usable for content week selection', async ({ page }) => {
  await seed(page);
  await page.goto('/ai/courses/course_project_002/plan');
  await page.getByRole('button', { name: 'Minta revisi', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Minta revisi rencana' });
  await dialog.getByRole('textbox', { name: 'Instruksi perbaikan' }).fill('Perjelas contoh minggu 5-8.');
  await dialog.getByRole('button', { name: 'Regenerasi rencana', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Rencana course · versi 2', exact: true })).toBeVisible();
  const week5 = page.getByRole('table').locator('tbody tr').nth(4);
  await expect(week5).toContainText('Disesuaikan: Perjelas contoh minggu 5-8.');
  await expect(week5).toContainText('CPMK-2');
  await expect(week5).toContainText('praktikum');
  await page.getByRole('button', { name: 'Setujui rencana', exact: true }).click();
  await expect(page.getByText('Disetujui', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Konten', exact: true }).click();
  await page.getByRole('radio', { name: 'Pilih minggu', exact: true }).check();
  const weeks = page.locator('.week-picker input');
  await expect(weeks).toHaveCount(16);
  await page.locator('.week-picker label').first().click();
  await expect(weeks.first()).toBeChecked();
  await page.getByRole('button', { name: 'Generate 1 minggu', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Tujuan pembelajaran', exact: true })).toBeVisible();
});
