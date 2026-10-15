import { test, expect } from '@playwright/test';

async function seed(page, token = 'mock-3-test', backend = 'mock-token:user_001') {
  await page.addInitScript(({ token, backend }) => {
    localStorage.setItem('agentic-lms.moodle-session', JSON.stringify({ token }));
    if (backend) localStorage.setItem('agentic-lms.token', backend);
  }, { token, backend });
}

test('Moodle session restores the same account after reload', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Username', { exact: true }).fill('mahasiswa');
  await page.getByLabel('Kata sandi', { exact: true }).fill('mahasiswa123');
  await page.getByRole('button', { name: 'Masuk', exact: true }).click();
  await expect(page.getByText('Ringkasan belajar', { exact: true })).toBeVisible();
  const token = await page.evaluate(() => localStorage.getItem('agentic-lms.moodle-session'));
  await page.reload();
  await expect(page.getByRole('button', { name: 'Menu pengguna' })).toContainText('Andi Saputra');
  expect(await page.evaluate(() => localStorage.getItem('agentic-lms.moodle-session'))).toBe(token);
  await page.getByRole('button', { name: 'Menu pengguna' }).click();
  await expect(page.getByRole('menuitem', { name: 'Generator AI' })).toHaveCount(0);
});

test('expired Moodle token returns to login and clears storage', async ({ page }) => {
  await seed(page, 'mock-999-expired');
  await page.goto('/my/courses');
  await expect(page.getByRole('heading', { name: 'Masuk ke akun Anda' })).toBeVisible();
  expect(await page.evaluate(() => [localStorage.getItem('agentic-lms.moodle-session'), localStorage.getItem('agentic-lms.token')])).toEqual([null, null]);
});

test('course search exposes empty state and recovers to real mock data', async ({ page }) => {
  await seed(page);
  await page.goto('/my/courses');
  await expect(page.getByRole('link', { name: /Pemrograman Web/ })).toBeVisible();
  await page.getByRole('searchbox', { name: 'Cari kursus' }).fill('course-tidak-ada');
  await expect(page.getByText('Tidak ada kursus yang cocok dengan pencarian.', { exact: true })).toBeVisible();
  await page.getByRole('searchbox', { name: 'Cari kursus' }).fill('Basis Data');
  await expect(page.getByRole('link', { name: /Basis Data/ })).toBeVisible();
  await expect(page.getByRole('link', { name: /Pemrograman Web/ })).toHaveCount(0);
  await page.getByRole('combobox', { name: 'Filter kursus' }).selectOption('past');
  await expect(page.getByText('Tidak ada kursus yang cocok dengan pencarian.', { exact: true })).toBeVisible();
  await page.getByRole('combobox', { name: 'Filter kursus' }).selectOption('all');
  await expect(page.getByRole('link', { name: /Basis Data/ })).toBeVisible();
});

test('menu links and browser history keep the current route consistent', async ({ page }) => {
  await seed(page);
  await page.goto('/my');
  const menu = page.getByRole('button', { name: 'Menu pengguna' });
  await menu.click();
  await page.getByRole('menuitem', { name: 'Kursus saya', exact: true }).click();
  await expect(page).toHaveURL(/\/my\/courses$/);
  await expect(page.getByRole('menu')).toHaveCount(0);
  await menu.click();
  await page.getByRole('menuitem', { name: 'Profil', exact: true }).click();
  await expect(page).toHaveURL(/\/user\/profile$/);
  await page.goBack();
  await expect(page.getByRole('heading', { name: 'Kursus saya', exact: true })).toBeVisible();
  await page.goForward();
  await expect(page).toHaveURL(/\/user\/profile$/);
});

test('revision dialog prevents background focus and Escape returns it to the trigger', async ({ page }) => {
  await seed(page);
  await page.goto('/ai/courses/course_project_002/plan');
  const trigger = page.getByRole('button', { name: 'Minta revisi', exact: true });
  await trigger.click();
  const dialog = page.getByRole('dialog', { name: 'Minta revisi rencana' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Regenerasi rencana', exact: true })).toBeDisabled();
  await dialog.getByRole('textbox').fill('Perjelas contoh minggu pertama.');
  await expect(dialog.getByRole('button', { name: 'Regenerasi rencana', exact: true })).toBeEnabled();
  for (const key of ['Tab', 'Shift+Tab']) {
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press(key);
      // Native dialogs may yield focus to browser chrome (activeElement=body).
      // Background page controls must never receive focus; the next Tab returns.
      const focus = await dialog.evaluate((element) => ({ inside: element.contains(document.activeElement), browser: document.activeElement === document.body }));
      expect(focus.inside || focus.browser).toBe(true);
      if (focus.browser) {
        await page.keyboard.press(key);
        expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true);
      }
    }
  }
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test('profile save updates shared data and shows success feedback', async ({ page }) => {
  await seed(page);
  await page.goto('/ai/profile');
  await page.getByLabel('Gaya mengajar', { exact: false }).fill('Diskusi studi kasus untuk pengujian FE-04.1');
  await page.getByRole('button', { name: 'Simpan profil', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Profil tersimpan.');
  await page.getByRole('link', { name: 'Project', exact: true }).click();
  await page.getByRole('link', { name: 'Preferensi mengajar', exact: true }).click();
  await expect(page.getByLabel('Gaya mengajar', { exact: false })).toHaveValue('Diskusi studi kasus untuk pengujian FE-04.1');
});

test('backend errors are visible while the independent Moodle session stays usable', async ({ page }) => {
  await seed(page, 'mock-3-test', 'expired-backend-token');
  await page.goto('/ai/profile');
  await expect(page.getByRole('alert')).toBeVisible();
  await page.getByRole('button', { name: 'Menu pengguna' }).click();
  await page.getByRole('menuitem', { name: 'Kursus saya', exact: true }).click();
  await expect(page.getByRole('link', { name: /Pemrograman Web/ })).toBeVisible();
});

const layouts = [
  ['/my/courses', 'Kursus saya'],
  ['/ai/profile', 'Profil Dosen'],
  ['/ai/courses/new', 'Course baru'],
  ['/course/2/participants', 'Pemrograman Web'],
  ['/ai/courses/course_project_001/plan', 'IF2105 — Pemrograman Web'],
];
for (const width of [375, 768, 1440]) {
  for (const [route, title] of layouts) {
    test('foundation layout ' + width + ' ' + route, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 900 });
      await seed(page);
      await page.goto(route);
      await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
      await expect(page.locator('main [role="status"]')).toHaveCount(0);
      const main = await page.locator('main').boundingBox();
      expect(main.x).toBeGreaterThanOrEqual(0);
      expect(main.x + main.width).toBeLessThanOrEqual(width + 1);
      for (const control of await page.locator('main input:visible, main select:visible, main textarea:visible').all()) {
        const box = await control.boundingBox();
        expect(box.x).toBeGreaterThanOrEqual(0);
        expect(box.x + box.width).toBeLessThanOrEqual(width + 1);
      }
      await expect(page.locator('aside')).toHaveCount(0);
      const menu = page.getByRole('button', { name: 'Menu pengguna' });
      await menu.click();
      const menuBox = await page.getByRole('menu').boundingBox();
      expect(menuBox.x).toBeGreaterThanOrEqual(0);
      expect(menuBox.x + menuBox.width).toBeLessThanOrEqual(width + 1);
      await page.keyboard.press('Escape');
      await expect(page.getByRole('menu')).toHaveCount(0);
      if (width === 375) {
        const file = testInfo.outputPath('foundation-mobile.png');
        await page.screenshot({ path: file, fullPage: true });
        await testInfo.attach('mobile layout', { path: file, contentType: 'image/png' });
      }
    });
  }
}
