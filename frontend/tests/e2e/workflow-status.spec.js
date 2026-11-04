import { test, expect } from '@playwright/test';

// FE-10.1: status workflow di tab Workflow Generator AI (mock backend).
async function seed(page) {
  await page.addInitScript(() => {
    localStorage.setItem('agentic-lms.moodle-session', JSON.stringify({ token: 'mock-3-test' }));
    localStorage.setItem('agentic-lms.token', 'mock-token:user_001');
  });
}
const pdf = (name) => ({ name, mimeType: 'application/pdf', buffer: Buffer.alloc(2048, 'a') });

for (const width of [375, 1440]) {
  test(`lecturer follows workflow stages from the RPS list at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await seed(page);
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto('/course/3/ai');
    await page.locator('form.upload input[type="file"]').setInputFiles(pdf('rps-status.pdf'));
    await page.getByRole('button', { name: 'Unggah & proses' }).click();
    const row = page.getByRole('list', { name: 'Daftar RPS' }).getByRole('listitem').filter({ hasText: 'rps-status.pdf' });
    await row.getByRole('link', { name: 'Pantau workflow' }).click({ timeout: 15000 });

    // Daftar dan detail dari GET /workflows dan GET /workflows/{id}.
    await expect(page).toHaveURL(/\/course\/3\/ai\/workflows\?workflow=/);
    const list = page.getByRole('list', { name: 'Daftar workflow' });
    await expect(list.getByRole('listitem').first()).toContainText('rps-status.pdf');
    const stages = page.getByRole('list', { name: 'Tahapan workflow' });
    await expect(stages.getByRole('listitem')).toHaveCount(8);
    await expect(stages.locator('[data-stage="rps_analysis"]')).toBeVisible();

    // Status berubah otomatis sampai selesai, tanpa memuat ulang halaman.
    await expect(stages.locator('[data-stage="rps_analysis"]')).toHaveAttribute('data-state', 'done', { timeout: 20000 });
    await expect(stages.locator('[data-stage="rps_processing"]')).toHaveAttribute('data-state', /done|pending/);
    await expect(list.getByText('Selesai', { exact: true }).first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(errors).toEqual([]);
  });
}

test('failed workflow is visually different and keeps its message', async ({ page }) => {
  await seed(page);
  await page.goto('/course/3/ai');
  await page.locator('form.upload input[type="file"]').setInputFiles(pdf('rps-gagal-analisis.pdf'));
  await page.getByRole('button', { name: 'Unggah & proses' }).click();
  const row = page.getByRole('list', { name: 'Daftar RPS' }).getByRole('listitem').filter({ hasText: 'rps-gagal-analisis.pdf' });
  await expect(row.getByText('Gagal', { exact: true })).toBeVisible({ timeout: 20000 });
  await row.getByRole('link', { name: 'Pantau workflow' }).click();
  const stages = page.getByRole('list', { name: 'Tahapan workflow' });
  await expect(stages.locator('[data-stage="rps_analysis"]')).toHaveAttribute('data-state', 'failed');
  await expect(page.getByRole('alert').filter({ hasText: 'Workflow gagal' })).toContainText('Analisis RPS gagal');
  await expect(page.locator('[data-marker="failed"]').first()).toContainText('✕');
});
