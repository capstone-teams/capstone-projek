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
    // Tanpa saklar: pengajar langsung dalam mode edit.
    await expect(page.getByRole('switch', { name: 'Mode edit' })).toHaveCount(0);

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

    // Tambah section.
    await page.getByRole('button', { name: '+ Tambah section' }).click();
    await expect(page.getByRole('heading', { name: 'New section' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(errors).toEqual([]);
  });
}

for (const width of [375, 1440]) {
  test(`teacher creates an assignment, a quiz and a text block via New activity pages at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await seed(page);
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto('/course/2');
    const week1 = page.locator('#section-1');
    const chooser = page.getByRole('dialog', { name: 'Add an activity or resource' });

    // Assignment: pemilih membuka halaman New Assignment seperti course/modedit.php.
    await week1.getByRole('button', { name: 'Tambah aktivitas atau sumber' }).click();
    await chooser.getByRole('button', { name: 'Assignment', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'New Assignment' })).toBeVisible();
    await expect(page.getByLabel('Breadcrumb aktivitas')).toHaveText('Minggu 1: Pengantar Pemrograman Web / New Assignment');
    await page.getByRole('button', { name: 'Save and return to course' }).click();
    await expect(page.getByText('You must supply a value here.')).toBeVisible();
    await expect(page.getByLabel('Assignment name')).toBeFocused();
    await page.getByLabel('Assignment name').fill('Tugas Ringkasan HTTP');
    const description = page.getByRole('textbox', { name: 'Description' });
    await description.click();
    await page.keyboard.type('Ringkas protokol HTTP.');
    await page.getByLabel('Online text').check();
    await page.getByRole('button', { name: 'Expand all' }).click();
    await page.getByLabel('Maximum grade').fill('80');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.getByRole('button', { name: 'Save and display' }).click();
    await expect(page.getByRole('heading', { name: 'Tugas Ringkasan HTTP' })).toBeVisible();
    await expect(page.getByText('Ringkas protokol HTTP.')).toBeVisible();

    // Quiz: Save and return to course.
    await page.goto('/course/2');
    await week1.getByRole('button', { name: 'Tambah aktivitas atau sumber' }).click();
    await chooser.getByRole('button', { name: 'Quiz', exact: true }).click();
    await page.getByLabel('Name', { exact: true }).fill('Kuis Pengantar HTTP');
    await page.getByRole('button', { name: 'Save and return to course' }).click();
    await expect(week1.getByRole('link', { name: 'Kuis Pengantar HTTP', exact: true })).toBeVisible();

    // Text and media area: tanpa Save and display.
    await week1.getByRole('button', { name: 'Tambah aktivitas atau sumber' }).click();
    await chooser.getByRole('button', { name: 'Text and media area', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Save and display' })).toHaveCount(0);
    await page.getByRole('textbox', { name: 'Text' }).click();
    await page.keyboard.type('Kumpulkan tugas sebelum tenggat.');
    await page.getByRole('button', { name: 'Save and return to course' }).click();
    await expect(week1.getByText('Kumpulkan tugas sebelum tenggat.', { exact: true })).toBeVisible();
    expect(errors).toEqual([]);
  });
}

test('activity chooser fits a phone screen', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 700 });
  await seed(page);
  await page.goto('/course/2');
  await page.locator('#section-1').getByRole('button', { name: 'Tambah aktivitas atau sumber' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('button', { name: 'Text and media area', exact: true })).toBeVisible();
  const box = await dialog.boundingBox();
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(375);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('students do not get edit controls', async ({ page }) => {
  await seed(page, 'mahasiswa');
  await page.goto('/course/2');
  await expect(page.getByRole('heading', { name: /Minggu 1/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /^Aksi untuk/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Tambah aktivitas atau sumber' })).toHaveCount(0);
});

for (const width of [375, 1440]) {
  test(`student adds an online text and file submission at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await seed(page, 'mahasiswa');
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto('/course/2');
    await page.locator('#section-4').getByRole('link', { name: 'Tugas 4: JavaScript Dasar', exact: true }).click();
    await page.getByRole('link', { name: 'Add submission' }).click();
    await expect(page.getByLabel('Breadcrumb aktivitas')).toContainText('Edit submission');
    await expect(page.getByText('Maximum file size: 1 MB, maximum number of files: 20')).toBeVisible();
    await expect(page.getByText('You can drag and drop files here to add them.')).toBeVisible();
    await expect(page.getByRole('menubar', { name: 'Menu editor' })).toBeVisible();

    // Editor: ketik, lalu tebalkan kata terakhir lewat toolbar.
    const editor = page.getByRole('textbox', { name: 'Online text' });
    await editor.click();
    await page.keyboard.type('Ringkasan event loop dan DOM');
    await expect(page.getByText('5 words')).toBeVisible();
    await page.keyboard.press('Shift+Control+ArrowLeft');
    await page.getByRole('button', { name: 'Bold' }).click();
    await expect(editor.locator('b, strong')).toHaveText('DOM');

    await page.getByLabel('Pilih file pengumpulan').setInputFiles({ name: 'laporan.pdf', mimeType: 'application/pdf', buffer: Buffer.alloc(2048) });
    await expect(page.getByRole('button', { name: /laporan\.pdf/ })).toBeVisible();
    await page.getByRole('button', { name: 'Save changes' }).click();

    await expect(page.getByText('Submitted for grading')).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Ringkasan event loop dan DOM' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Edit submission' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(errors).toEqual([]);
  });
}
