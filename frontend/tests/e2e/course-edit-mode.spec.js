import { test, expect } from '@playwright/test';

// Edit mode halaman kursus (mock Moodle). dosen = editingteacher kursus 2 & 4.
async function seed(page, role = 'dosen') {
  await page.addInitScript(({ role }) => {
    localStorage.setItem('agentic-lms.moodle-session', JSON.stringify({ token: role === 'dosen' ? 'mock-3-test' : 'mock-5-test' }));
    localStorage.setItem('agentic-lms.token', role === 'dosen' ? 'mock-token:user_001' : 'mock-token:user_002');
  }, { role });
}

for (const width of [375, 1440]) {
  test(`teacher edits the course with keyboard and menus at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await seed(page);
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto('/course/2');
    const toggle = page.getByRole('switch', { name: 'Mode edit' });
    await expect(toggle).toHaveAttribute('aria-checked', 'false');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-checked', 'true');

    // Menu ⋮ dapat dipakai dengan keyboard: panah bawah, Escape mengembalikan fokus.
    const menuButton = page.getByRole('button', { name: 'Aksi untuk Kuis 3' });
    await menuButton.click();
    const menu = page.getByRole('menu', { name: 'Aksi untuk Kuis 3' });
    await expect(menu.getByRole('menuitem').first()).toBeFocused();
    await page.keyboard.press('ArrowDown');
    await expect(menu.getByRole('menuitem', { name: 'Pindahkan' })).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(menu).toHaveCount(0);
    await expect(menuButton).toBeFocused();

    // Sembunyikan → badge; geser ke kanan → indentasi.
    await menuButton.click();
    await menu.getByRole('menuitem', { name: 'Sembunyikan' }).click();
    const quiz = page.locator('li', { has: page.getByRole('button', { name: 'Aksi untuk Kuis 3' }) });
    await expect(quiz.getByText('Disembunyikan dari mahasiswa', { exact: true })).toBeVisible();
    await menuButton.click();
    await menu.getByRole('menuitem', { name: 'Geser ke kanan' }).click();
    await expect(quiz).toHaveCSS('margin-left', '24px');

    // Ganti nama lewat pensil.
    await page.getByRole('button', { name: 'Ubah nama Kuis 3' }).click();
    await page.getByRole('textbox', { name: 'Nama baru untuk Kuis 3' }).fill('Kuis Minggu 3');
    await page.keyboard.press('Enter');
    await expect(page.getByRole('link', { name: 'Kuis Minggu 3', exact: true })).toBeVisible();

    // Hapus dengan konfirmasi.
    await page.getByRole('button', { name: 'Aksi untuk Kuis Minggu 3' }).click();
    await page.getByRole('menuitem', { name: 'Hapus' }).click();
    const dialog = page.getByRole('dialog', { name: 'Hapus aktivitas?' });
    await dialog.getByRole('button', { name: 'Hapus', exact: true }).click();
    await expect(page.getByRole('link', { name: 'Kuis Minggu 3', exact: true })).toHaveCount(0);

    // Tambah section, lalu matikan Edit mode.
    await page.getByRole('button', { name: '+ Tambah section' }).click();
    await expect(page.getByRole('heading', { name: 'New section' })).toBeVisible();
    await toggle.click();
    await expect(page.getByRole('button', { name: /^Aksi untuk/ })).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(errors).toEqual([]);
  });
}

test('teacher creates an assignment, a quiz and a text block from the activity chooser', async ({ page }) => {
  await seed(page);
  await page.goto('/course/2');
  await page.getByRole('switch', { name: 'Mode edit' }).click();
  const week1 = page.locator('#section-1');
  await week1.getByRole('button', { name: 'Tambah aktivitas atau sumber' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading', { name: 'Add an activity or resource' })).toBeVisible();
  await dialog.getByRole('button', { name: 'Assignment', exact: true }).click();
  await dialog.getByRole('button', { name: 'Simpan tugas' }).click();
  await expect(dialog.getByText('Nama tugas wajib diisi.', { exact: true })).toBeVisible();
  await dialog.getByLabel(/^Nama tugas/).fill('Tugas Ringkasan HTTP');
  await dialog.getByLabel('Tenggat').fill('2026-11-30T23:59');
  await dialog.getByRole('button', { name: 'Simpan tugas' }).click();
  await expect(dialog).toHaveCount(0);
  const created = week1.getByRole('link', { name: 'Tugas Ringkasan HTTP', exact: true });
  await expect(created).toBeVisible();

  await week1.getByRole('button', { name: 'Tambah aktivitas atau sumber' }).click();
  await dialog.getByRole('button', { name: 'Quiz', exact: true }).click();
  await dialog.getByLabel(/^Nama kuis/).fill('Kuis Pengantar HTTP');
  await dialog.getByRole('button', { name: 'Simpan kuis' }).click();
  await expect(week1.getByRole('link', { name: 'Kuis Pengantar HTTP', exact: true })).toBeVisible();

  await week1.getByRole('button', { name: 'Tambah aktivitas atau sumber' }).click();
  await dialog.getByRole('button', { name: 'Text and media area', exact: true }).click();
  await dialog.getByLabel(/^Isi/).fill('Kumpulkan tugas sebelum tenggat.');
  await dialog.getByRole('button', { name: 'Simpan', exact: true }).click();
  await expect(week1.getByText('Kumpulkan tugas sebelum tenggat.', { exact: true })).toBeVisible();

  // Tugas baru dapat dibuka seperti aktivitas lain.
  await created.click();
  await expect(page.getByRole('heading', { name: 'Tugas Ringkasan HTTP' })).toBeVisible();
});

test('activity chooser fits a phone screen', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 700 });
  await seed(page);
  await page.goto('/course/2');
  await page.getByRole('switch', { name: 'Mode edit' }).click();
  await page.locator('#section-1').getByRole('button', { name: 'Tambah aktivitas atau sumber' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('button', { name: 'Text and media area', exact: true })).toBeVisible();
  const box = await dialog.boundingBox();
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(375);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('students and non-editing teachers do not get Edit mode', async ({ page }) => {
  await seed(page, 'mahasiswa');
  await page.goto('/course/2');
  await expect(page.getByRole('heading', { name: /Minggu 1/ })).toBeVisible();
  await expect(page.getByRole('switch', { name: 'Mode edit' })).toHaveCount(0);
});
