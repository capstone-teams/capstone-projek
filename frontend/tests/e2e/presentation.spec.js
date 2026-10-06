import { test, expect } from '@playwright/test';

for (const width of [375, 768, 1440]) {
  for (const route of ['/login', '/my', '/ai/courses/course_project_001/content']) {
    test('approved presentation ' + width + ' ' + route, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 900 });
      if (route !== '/login') await page.addInitScript(() => {
        localStorage.setItem('agentic-lms.moodle-session', JSON.stringify({ token: 'mock-3-test' }));
        localStorage.setItem('agentic-lms.token', 'mock-token:user_001');
      });
      await page.goto(route);
      const ready = route === '/login' ? 'Masuk ke akun Anda' : route === '/my' ? 'Kursus yang Anda ajar' : 'Tujuan pembelajaran';
      await expect(page.getByText(ready, { exact: true })).toBeVisible();
      const header = page.locator('header').first();
      await expect(header).toHaveCSS('background-color', 'rgb(255, 255, 255)');
      await expect(header).toHaveCSS('height', '64px');
      await expect(page.getByRole('navigation', { name: 'Navigasi utama', exact: true })).toHaveCount(0);
      await expect(page.locator('aside')).toHaveCount(0);
      const bounds = await page.locator('main').boundingBox();
      expect(bounds.x).toBeGreaterThanOrEqual(0);
      expect(bounds.x + bounds.width).toBeLessThanOrEqual(width + 1);
      if (route === '/login') {
        await expect(page.getByRole('button', { name: 'Masuk', exact: true })).toHaveCSS('background-color', 'rgb(29, 78, 216)');
        await expect(page.getByLabel('Username', { exact: true })).toHaveCSS('border-radius', '6px');
      }
      await testInfo.attach('current-presentation', { body: await page.screenshot({ fullPage: true }), contentType: 'image/png' });
    });
  }
}
