import { expect, test, type Page } from '@playwright/test'

const routes = [
  '/login', '/dashboard', '/rps-analysis', '/course-plan', '/weekly-content',
  '/material-view', '/student/courses', '/student/course', '/student/week',
]

async function login(page: Page, username: string, password = 'password123') {
  await page.goto('/login')
  await page.getByLabel('Username', { exact: true }).fill(username)
  await page.getByLabel('Kata sandi', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Masuk', exact: true }).last().click()
}

async function mockCourseService(page: Page, overrides: string) {
  // Replace the service binding for this browser context; pages and hooks remain real.
  await page.route('**/src/services/index.ts', (route) => route.fulfill({
    contentType: 'application/javascript',
    body: `import { mockCourseService } from '/src/services/mockCourseService.ts';
      import { ApiError } from '/src/services/apiError.ts';
      let recovered = false;
      window.addEventListener('foundation:recover', () => { recovered = true; });
      export const courseService = { ...mockCourseService, ${overrides} };`,
  }))
}

test.describe('Application shell and development routes', () => {
  for (const route of routes) {
    test(`${route} renders without a backend or browser exception`, async ({ page }) => {
      const errors: string[] = []
      const apiRequests: string[] = []
      page.on('pageerror', (error) => errors.push(error.message))
      page.on('request', (request) => {
        if (new URL(request.url()).pathname.startsWith('/api/')) apiRequests.push(request.url())
      })
      await page.goto(route)
      await expect(page.locator('h1')).toBeVisible()
      await expect(page).toHaveTitle(/LMS ITK/)
      await expect(page.getByRole('status')).toHaveCount(0)
      expect(errors).toEqual([])
      expect(apiRequests).toEqual([])
    })
  }

  for (const [username, path] of [['dosen', '/dashboard'], ['mahasiswa', '/student/courses']]) {
    test(`mock login navigates ${username} to its landing page`, async ({ page }) => {
      await login(page, username)
      await expect(page).toHaveURL(new RegExp(`${path}$`))
      await expect(page.locator('h1')).toBeVisible()
    })
  }

  test('unknown demo username stays on the login form with feedback', async ({ page }) => {
    await login(page, 'tidak-terdaftar')
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByText('Username harus berupa "dosen" atau "mahasiswa".')).toBeVisible()
  })

  test('login inputs have accessible names', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByLabel('Username', { exact: true })).toBeVisible()
    await expect(page.getByLabel('Kata sandi', { exact: true })).toBeVisible()
  })

  test('keyboard course navigation and browser history update URL and page', async ({ page }) => {
    await page.goto('/dashboard?hasCourses=true')
    const course = page.getByRole('button', { name: /IF201405.*Aljabar Linear dan Geometri/ })
    await course.focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/course-plan$/)
    await expect(page.getByRole('heading', { name: 'Aljabar Linear dan Geometri', exact: true })).toBeVisible()
    await page.goBack()
    await expect(page.getByRole('heading', { name: 'Mata Kuliah Dosen', exact: true })).toBeVisible()
    await page.goForward()
    await expect(page).toHaveURL(/\/course-plan$/)
    await expect(page).toHaveTitle(/Course Plan/)
  })
})

test.describe('Shared modal and state', () => {
  test('modal traps focus, closes with Escape and returns focus to its opener', async ({ page }) => {
    await page.goto('/dashboard')
    const opener = page.getByRole('button', { name: '+ Upload RPS', exact: true })
    await opener.focus()
    await opener.click()
    const dialog = page.getByRole('dialog', { name: 'Upload RPS', exact: true })
    await expect(dialog).toBeVisible()
    await expect(page.locator('body')).toHaveCSS('overflow', 'hidden')
    const close = dialog.getByRole('button', { name: 'Tutup modal', exact: true })
    await close.focus()
    await page.keyboard.press('Shift+Tab')
    await expect(dialog.getByRole('button').last()).toBeFocused()
    await page.keyboard.press('Tab')
    await expect(close).toBeFocused()
    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)
    await expect(page.locator('body')).not.toHaveCSS('overflow', 'hidden')
    await expect(opener).toBeFocused()
  })

  test('profile changes update the shared header and produce dismissible feedback', async ({ page }) => {
    await page.goto('/dashboard')
    await page.locator('button[aria-haspopup="menu"]').click()
    await page.getByRole('menuitem', { name: 'Profil Dosen', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: 'Profil Dosen', exact: true })
    await dialog.locator('input[type="text"]').first().fill('Dosen Verifikasi')
    await dialog.getByRole('button', { name: /Simpan/ }).click()
    await expect(dialog).toHaveCount(0)
    await expect(page.locator('button[aria-haspopup="menu"]')).toContainText('Dosen Verifikasi')
    await expect(page.getByText('Profil dan preferensi AI dosen berhasil disimpan.')).toBeVisible()
    await page.getByRole('button', { name: 'Tutup notifikasi', exact: true }).click()
    await expect(page.getByText('Profil dan preferensi AI dosen berhasil disimpan.')).toHaveCount(0)
  })
})

test.describe('Service request states in real pages', () => {
  test('pending data displays loading, then resolves to course cards', async ({ page }) => {
    await mockCourseService(page, `async listStudentCourses() {
      await new Promise(resolve => window.addEventListener('foundation:release', resolve, { once: true }));
      return mockCourseService.listStudentCourses();
    }`)
    await page.goto('/student/courses')
    await expect(page.getByRole('status')).toHaveText('Memuat data...')
    await page.evaluate(() => window.dispatchEvent(new Event('foundation:release')))
    await expect(page.getByRole('heading', { name: 'Aljabar Linear dan Geometri', exact: true })).toBeVisible()
    await expect(page.getByRole('status')).toHaveCount(0)
  })

  test('a rejected service displays error and retry recovers to success', async ({ page }) => {
    await mockCourseService(page, `async listStudentCourses() {
      if (!recovered) throw new ApiError('Koneksi ke server gagal.', 'network');
      return mockCourseService.listStudentCourses();
    }`)
    await page.goto('/student/courses')
    await expect(page.getByRole('alert')).toContainText('Koneksi ke server gagal.')
    await page.evaluate(() => window.dispatchEvent(new Event('foundation:recover')))
    await page.getByRole('button', { name: 'Coba lagi', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Aljabar Linear dan Geometri', exact: true })).toBeVisible()
    await expect(page.getByRole('alert')).toHaveCount(0)
  })

  for (const [path, method] of [
    ['/student/courses', 'listStudentCourses'],
    ['/dashboard?hasCourses=true', 'listInstructorCourses'],
  ]) {
    test(`${method} returning an empty list displays an explicit empty state`, async ({ page }) => {
      await mockCourseService(page, `async ${method}() { return []; }`)
      await page.goto(path)
      await expect(page.getByRole('heading', { name: 'Belum ada mata kuliah', exact: true })).toBeVisible()
      await expect(page.getByRole('status')).toHaveCount(0)
    })
  }

  test('a pending service resolving after navigation does not replace the new page', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (error) => errors.push(error.message))
    await mockCourseService(page, `async listStudentCourses() {
      await new Promise(resolve => window.addEventListener('foundation:release', resolve, { once: true }));
      return mockCourseService.listStudentCourses();
    }`)
    await page.goto('/student/courses')
    await expect(page.getByRole('status')).toBeVisible()
    await page.locator('button[aria-haspopup="menu"]').click()
    await page.getByRole('menuitem', { name: /Dosen \(/ }).click()
    await expect(page.getByRole('heading', { name: 'Mata Kuliah Dosen', exact: true })).toBeVisible()
    await page.evaluate(() => window.dispatchEvent(new Event('foundation:release')))
    await expect(page.getByRole('heading', { name: 'Mata Kuliah Dosen', exact: true })).toBeVisible()
    expect(errors).toEqual([])
  })
})

test.describe('Responsive layout', () => {
  for (const viewport of [
    { width: 375, height: 812 },
    { width: 768, height: 1024 },
    { width: 1440, height: 900 },
  ]) {
    test(`routes and upload dialog fit ${viewport.width}px`, async ({ page }, testInfo) => {
      await page.setViewportSize(viewport)
      for (const route of routes) {
        await page.goto(route)
        const heading = page.locator('h1')
        await expect(heading).toBeVisible()
        const bounds = await heading.boundingBox()
        expect(bounds).not.toBeNull()
        expect(bounds!.x).toBeGreaterThanOrEqual(0)
        expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(viewport.width + 1)
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width)
      }
      await page.goto('/dashboard')
      await page.getByRole('button', { name: '+ Upload RPS', exact: true }).click()
      const dialog = page.getByRole('dialog', { name: 'Upload RPS', exact: true })
      await expect(dialog).toBeVisible()
      const bounds = await dialog.boundingBox()
      expect(bounds!.x).toBeGreaterThanOrEqual(0)
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(viewport.width + 1)
      await expect(dialog.getByRole('button', { name: 'Tutup modal' })).toBeInViewport()
      await page.keyboard.press('Escape')
      await testInfo.attach(`dashboard-${viewport.width}px`, { body: await page.screenshot(), contentType: 'image/png' })
    })
  }
})

test.describe('Unintegrated authentication and route dependencies', () => {
  test('anonymous users cannot open an instructor route directly', async ({ page }) => {
    test.fail(true, 'FE-02 protected routes are not integrated; App currently grants a role from the URL.')
    await page.goto('/dashboard')
    await expect(page.locator('h1')).toBeVisible()
    await expect(page).toHaveURL(/\/login$/)
  })

  test('invalid mock passwords cannot authenticate', async ({ page }) => {
    test.fail(true, 'FE-02 auth service is not integrated; the approved demo explicitly ignores passwords.')
    await login(page, 'dosen', 'wrong-password')
    await expect(page.locator('h1')).toBeVisible()
    await expect(page).toHaveURL(/\/login$/)
  })

  test('student sessions cannot gain instructor access through the URL', async ({ page }) => {
    test.fail(true, 'FE-02 role guard and FE-03.1 session state are not integrated.')
    await login(page, 'mahasiswa')
    await expect(page).toHaveURL(/\/student\/courses$/)
    await page.goto('/dashboard')
    await expect(page.locator('h1')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Mata Kuliah Dosen', exact: true })).toBeHidden()
  })

  test('logout prevents Back from reopening a protected page', async ({ page }) => {
    test.fail(true, 'FE-02 route guard is not integrated; logout currently resets demo state only.')
    await login(page, 'dosen')
    await expect(page).toHaveURL(/\/dashboard$/)
    await page.locator('button[aria-haspopup="menu"]').click()
    await page.getByRole('menuitem', { name: /Keluar/ }).click()
    await expect(page).toHaveURL(/\/login$/)
    await page.goBack()
    await expect(page.getByRole('heading', { name: 'Mata Kuliah Dosen', exact: true })).toBeHidden()
  })

  test('unknown routes do not silently enter the instructor area', async ({ page }) => {
    test.fail(true, 'FE-02 not-found behavior is not integrated; resolveAppPath falls back to dashboard.')
    await page.goto('/route-that-does-not-exist')
    await expect(page.locator('h1')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Mata Kuliah Dosen', exact: true })).toBeHidden()
  })
})
