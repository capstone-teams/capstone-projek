import fs from 'node:fs'
import path from 'node:path'
import { test, describe } from 'node:test'
import assert from 'node:assert/strict'
import type { AppPath } from '../src/types/navigation.ts'
import { APP_ROUTES } from '../src/types/navigation.ts'
import {
  WEEKS_DATA,
  DOSEN_COURSES,
  MAHASISWA_COURSES,
  RPS_ANALYSIS_DATA,
} from '../src/data/courseData.ts'
import { DOSEN_PROFILE, MAHASISWA_PROFILE } from '../src/types/auth.ts'
import type { CoursePlanStage, WeeklyContentStage } from '../src/types/course.ts'
import {
  resolveAppPath,
  getRoleForPath,
  isPathAllowedForRole,
  getDefaultPathForRole,
  getBreadcrumbTrail,
} from '../src/utils/navigation.ts'
import {
  transitionCoursePlanStage,
  isValidCoursePlanTransition,
  transitionWeeklyContentStage,
  isValidWeeklyContentTransition,
} from '../src/utils/lifecycle.ts'

describe('Domain-Driven Navigation & Semantic Routes', () => {
  test('has exactly 8 semantic paths defined in APP_ROUTES', () => {
    const routes = Object.keys(APP_ROUTES) as AppPath[]
    assert.equal(routes.length, 8)
  })

  test('covers all standard application routes', () => {
    const expectedPaths: AppPath[] = [
      '/login',
      '/dashboard',
      '/rps-analysis',
      '/course-plan',
      '/weekly-content',
      '/student/courses',
      '/student/course',
      '/student/week',
    ]

    for (const p of expectedPaths) {
      assert.ok(APP_ROUTES[p], `Route for ${p} must be defined`)
      assert.equal(APP_ROUTES[p].path, p)
      assert.ok(APP_ROUTES[p].title.includes('LMS ITK'))
    }
  })

  test('accurately sets route titles reflecting the course hierarchy', () => {
    assert.equal(
      APP_ROUTES['/course-plan'].title,
      'Keamanan Siber (Course Plan) — LMS ITK'
    )
    assert.equal(
      APP_ROUTES['/rps-analysis'].title,
      'Hasil Analisis RPS — Keamanan Siber — LMS ITK'
    )
    assert.equal(
      APP_ROUTES['/weekly-content'].title,
      'Detail Konten Mingguan — LMS ITK'
    )
  })

  test('categorizes routes into public, dosen, and mahasiswa roles', () => {
    const publicRoutes = Object.values(APP_ROUTES).filter((r) => r.role === 'public')
    const dosenRoutes = Object.values(APP_ROUTES).filter((r) => r.role === 'dosen')
    const mhsRoutes = Object.values(APP_ROUTES).filter((r) => r.role === 'mahasiswa')

    assert.equal(publicRoutes.length, 1) // /login
    assert.equal(dosenRoutes.length, 4) // /dashboard, /rps-analysis, /course-plan, /weekly-content
    assert.equal(mhsRoutes.length, 3) // /student/courses, /student/course, /student/week
  })

  test('verifies role permissions and guards using navigation utils', () => {
    assert.equal(isPathAllowedForRole('/login', 'dosen'), true)
    assert.equal(isPathAllowedForRole('/login', 'mahasiswa'), true)

    assert.equal(isPathAllowedForRole('/dashboard', 'dosen'), true)
    assert.equal(isPathAllowedForRole('/dashboard', 'mahasiswa'), false)

    assert.equal(isPathAllowedForRole('/student/courses', 'mahasiswa'), true)
    assert.equal(isPathAllowedForRole('/student/courses', 'dosen'), false)

    assert.equal(getDefaultPathForRole('dosen'), '/dashboard')
    assert.equal(getDefaultPathForRole('mahasiswa'), '/student/courses')
    assert.equal(getRoleForPath('/rps-analysis'), 'dosen')
    assert.equal(getRoleForPath('/student/week'), 'mahasiswa')
  })
})

describe('Course Data & Syllabus Integrity', () => {
  test('contains exactly 16 semester weeks in syllabus', () => {
    assert.equal(WEEKS_DATA.length, 16)
    WEEKS_DATA.forEach((w, idx) => {
      assert.equal(w.weekNumber, idx + 1)
      assert.ok(w.title.length > 0)
      assert.ok(w.duration.includes(`Minggu ${idx + 1 < 10 ? `0${idx + 1}` : idx + 1}`))
    })
  })

  test('contains Keamanan Siber as primary course in Dosen and Mahasiswa data', () => {
    const dosenCourse = DOSEN_COURSES.find((c) => c.code === 'IF403')
    const mhsCourse = MAHASISWA_COURSES.find((c) => c.code === 'IF403')

    assert.ok(dosenCourse, 'Dosen course IF403 must exist')
    assert.equal(dosenCourse.name, 'Keamanan Siber')
    assert.ok(mhsCourse, 'Mahasiswa course IF403 must exist')
    assert.equal(mhsCourse.name, 'Keamanan Siber')
  })

  test('has consistent course catalog across dosen and mahasiswa', () => {
    const dosenCodes = DOSEN_COURSES.map((c) => c.code).sort()
    const mhsCodes = MAHASISWA_COURSES.map((c) => c.code).sort()
    assert.deepEqual(dosenCodes, mhsCodes)
  })

  test('contains valid RPS analysis data for Keamanan Siber', () => {
    assert.equal(RPS_ANALYSIS_DATA.courseCode, 'IF403')
    assert.equal(RPS_ANALYSIS_DATA.sks, 3)
    assert.equal(RPS_ANALYSIS_DATA.totalWeeks, 16)
    assert.ok(RPS_ANALYSIS_DATA.targetCpl.length > 0)
    assert.ok(RPS_ANALYSIS_DATA.fileName.endsWith('.pdf'))
  })
})

describe('User Profiles & Institutional Personas', () => {
  test('defines valid Dosen persona for Muchammad Chandra Cahyo Utomo', () => {
    assert.equal(DOSEN_PROFILE.name, 'Muchammad Chandra Cahyo Utomo, S. Kom., M. Kom.')
    assert.equal(DOSEN_PROFILE.role, 'dosen')
    assert.equal(DOSEN_PROFILE.avatarInitial, 'MC')
    assert.ok(DOSEN_PROFILE.email.endsWith('@itk.ac.id'))
    assert.ok(DOSEN_PROFILE.identifier.length > 10)
  })

  test('defines valid Mahasiswa persona for Noel Sipayung', () => {
    assert.equal(MAHASISWA_PROFILE.name, 'Noel Sipayung')
    assert.equal(MAHASISWA_PROFILE.role, 'mahasiswa')
    assert.equal(MAHASISWA_PROFILE.avatarInitial, 'NS')
    assert.ok(MAHASISWA_PROFILE.email.includes('student.itk.ac.id'))
    assert.equal(MAHASISWA_PROFILE.identifier, '11211045')
  })
})

describe('Course Plan Lifecycle State Machine', () => {
  test('transitions sequentially: empty -> review -> approved -> published', () => {
    let stage: CoursePlanStage = 'empty'

    stage = transitionCoursePlanStage(stage, 'GENERATE')
    assert.equal(stage, 'review')

    stage = transitionCoursePlanStage(stage, 'APPROVE')
    assert.equal(stage, 'approved')

    stage = transitionCoursePlanStage(stage, 'PUBLISH')
    assert.equal(stage, 'published')
  })

  test('handles revision without breaking current stage', () => {
    const stage: CoursePlanStage = 'review'
    const nextStage = transitionCoursePlanStage(stage, 'REVISE')
    assert.equal(nextStage, 'review')
  })

  test('allows resetting to empty from any stage', () => {
    const stages: CoursePlanStage[] = ['empty', 'review', 'approved', 'published']
    for (const s of stages) {
      assert.equal(transitionCoursePlanStage(s, 'RESET'), 'empty')
      assert.equal(isValidCoursePlanTransition(s, 'empty'), true)
    }
  })

  test('rejects illegal transitions with descriptive error', () => {
    assert.throws(() => transitionCoursePlanStage('empty', 'APPROVE'), /Cannot approve/)
    assert.throws(() => transitionCoursePlanStage('empty', 'PUBLISH'), /Cannot publish/)
    assert.throws(() => transitionCoursePlanStage('approved', 'GENERATE'), /Cannot generate/)
    assert.throws(() => transitionCoursePlanStage('published', 'APPROVE'), /Cannot approve/)

    assert.equal(isValidCoursePlanTransition('empty', 'approved'), false)
    assert.equal(isValidCoursePlanTransition('empty', 'published'), false)
    assert.equal(isValidCoursePlanTransition('review', 'published'), false)
  })
})

describe('Weekly Content Lifecycle State Machine', () => {
  test('transitions sequentially: empty -> review -> synced', () => {
    let stage: WeeklyContentStage = 'empty'

    stage = transitionWeeklyContentStage(stage, 'GENERATE')
    assert.equal(stage, 'review')

    stage = transitionWeeklyContentStage(stage, 'SYNC')
    assert.equal(stage, 'synced')
  })

  test('handles revision during review stage', () => {
    const stage: WeeklyContentStage = 'review'
    const nextStage = transitionWeeklyContentStage(stage, 'REVISE')
    assert.equal(nextStage, 'review')
  })

  test('allows resetting to empty from any stage', () => {
    const stages: WeeklyContentStage[] = ['empty', 'review', 'synced']
    for (const s of stages) {
      assert.equal(transitionWeeklyContentStage(s, 'RESET'), 'empty')
      assert.equal(isValidWeeklyContentTransition(s, 'empty'), true)
    }
  })

  test('rejects illegal transitions with descriptive error', () => {
    assert.throws(() => transitionWeeklyContentStage('empty', 'SYNC'), /Cannot sync/)
    assert.throws(() => transitionWeeklyContentStage('synced', 'GENERATE'), /Cannot generate/)

    assert.equal(isValidWeeklyContentTransition('empty', 'synced'), false)
    assert.equal(isValidWeeklyContentTransition('synced', 'review'), false)
  })
})

describe('Path Resolution & Fallback Resilience', () => {
  test('resolves known path to itself', () => {
    assert.equal(resolveAppPath('/course-plan'), '/course-plan')
    assert.equal(resolveAppPath('/student/courses'), '/student/courses')
    assert.equal(resolveAppPath('/rps-analysis'), '/rps-analysis')
  })

  test('falls back unknown, null, or empty paths to /dashboard', () => {
    assert.equal(resolveAppPath(''), '/dashboard')
    assert.equal(resolveAppPath(null), '/dashboard')
    assert.equal(resolveAppPath(undefined), '/dashboard')
    assert.equal(resolveAppPath('/unknown-screen'), '/dashboard')
    assert.equal(resolveAppPath('/ITK-03'), '/dashboard')
    assert.equal(resolveAppPath('/random/deep/path'), '/dashboard')
  })
})

describe('Breadcrumb & Route Navigation Hierarchy', () => {
  test('Login route has simple Masuk breadcrumb', () => {
    const trail = getBreadcrumbTrail('/login')
    assert.equal(trail.length, 1)
    assert.deepEqual(trail[0], { label: 'Masuk' })
  })

  test('Course Plan (Keamanan Siber) is direct child of Dashboard', () => {
    const trail = getBreadcrumbTrail('/course-plan')
    assert.equal(trail.length, 2)
    assert.deepEqual(trail[0], { label: 'Dashboard', path: '/dashboard' })
    assert.deepEqual(trail[1], { label: 'Keamanan Siber' })
    assert.equal(trail[1].path, undefined, 'Active crumb must not have a link path')
  })

  test('Hasil Analisis RPS is sub-page under Keamanan Siber (Course Plan)', () => {
    const trail = getBreadcrumbTrail('/rps-analysis')
    assert.equal(trail.length, 3)
    assert.deepEqual(trail[0], { label: 'Dashboard', path: '/dashboard' })
    assert.deepEqual(trail[1], { label: 'Keamanan Siber', path: '/course-plan' })
    assert.deepEqual(trail[2], { label: 'Hasil Analisis RPS' })
    assert.equal(trail[2].path, undefined, 'Active crumb must not have a link path')
  })

  test('Detail Minggu 03 is sub-page under Keamanan Siber (Course Plan)', () => {
    const trail = getBreadcrumbTrail('/weekly-content')
    assert.equal(trail.length, 3)
    assert.deepEqual(trail[0], { label: 'Dashboard', path: '/dashboard' })
    assert.deepEqual(trail[1], { label: 'Keamanan Siber', path: '/course-plan' })
    assert.deepEqual(trail[2], { label: 'Detail Minggu 03' })
    assert.equal(trail[2].path, undefined, 'Active crumb must not have a link path')
  })

  test('student courses mirror the same hierarchical pattern', () => {
    const coursesTrail = getBreadcrumbTrail('/student/courses')
    assert.deepEqual(coursesTrail, [{ label: 'Mata Kuliah' }])

    const courseTrail = getBreadcrumbTrail('/student/course')
    assert.deepEqual(courseTrail, [
      { label: 'Mata Kuliah', path: '/student/courses' },
      { label: 'Keamanan Siber' },
    ])

    const weekTrail = getBreadcrumbTrail('/student/week')
    assert.deepEqual(weekTrail, [
      { label: 'Mata Kuliah', path: '/student/courses' },
      { label: 'Keamanan Siber', path: '/student/course' },
      { label: 'Minggu 03' },
    ])
  })
})

describe('Component Breadcrumb & Heading Implementation Consistency', () => {
  test('CoursePlanPage has Keamanan Siber as current breadcrumb, main title, and Dashboard back-link', () => {
    const file = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/course-plan/CoursePlanPage.tsx'),
      'utf8'
    )
    assert.match(file, /onClick=\{[^{}]*onNavigate\('\/dashboard'\)[^{}]*\}[\s\S]*?Dashboard/)
    assert.match(file, /<span className=\{styles\.breadcrumbCurrent\}>Keamanan Siber<\/span>/)
    assert.doesNotMatch(file, /<span className=\{styles\.breadcrumbCurrent\}>Course Plan<\/span>/)
    assert.match(file, /<h1 className=\{styles\.pageTitle\}>Keamanan Siber<\/h1>/)
    assert.match(file, /Course Plan · 16 pertemuan · IF403 · 3 SKS/)
    assert.match(file, /onNavigate\('\/rps-analysis'\)/)
  })

  test('RpsAnalysisPage links Keamanan Siber breadcrumb to /course-plan and has Kembali ke Course Plan button', () => {
    const file = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/rps/RpsAnalysisPage.tsx'),
      'utf8'
    )
    assert.match(file, /onClick=\{[^{}]*onNavigate\('\/dashboard'\)[^{}]*\}[\s\S]*?Dashboard/)
    assert.match(file, /onClick=\{[^{}]*onNavigate\('\/course-plan'\)[^{}]*\}[\s\S]*?\{RPS_ANALYSIS_DATA\.courseName\}/)
    assert.match(file, /<span className=\{styles\.breadcrumbCurrent\}>Hasil Analisis RPS<\/span>/)
    assert.match(file, /onClick=\{[^{}]*onNavigate\('\/course-plan'\)[^{}]*\}[\s\S]*?Kembali ke Course Plan/)
  })

  test('WeekDetailPage links Keamanan Siber breadcrumb to /course-plan and has Kembali ke Course Plan button', () => {
    const file = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/weekly-content/WeekDetailPage.tsx'),
      'utf8'
    )
    assert.match(file, /onClick=\{[^{}]*onNavigate\('\/dashboard'\)[^{}]*\}[\s\S]*?Dashboard/)
    assert.match(file, /onClick=\{[^{}]*onNavigate\('\/course-plan'\)[^{}]*\}[\s\S]*?Keamanan Siber/)
    assert.match(file, /<span className=\{styles\.breadcrumbCurrent\}>Detail Minggu 03<\/span>/)
    assert.match(file, /onClick=\{[^{}]*onNavigate\('\/course-plan'\)[^{}]*\}[\s\S]*?Kembali ke Course Plan/)
  })

  test('Student detail pages have consistent breadcrumb hierarchies', () => {
    const courseFile = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/student/StudentCourseDetailPage.tsx'),
      'utf8'
    )
    assert.match(courseFile, /onClick=\{[^{}]*onNavigate\('\/student\/courses'\)[^{}]*\}[\s\S]*?Mata Kuliah/)
    assert.match(courseFile, /<span className=\{styles\.breadcrumbCurrent\}>Keamanan Siber<\/span>/)

    const weekFile = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/student/StudentWeekDetailPage.tsx'),
      'utf8'
    )
    assert.match(weekFile, /onClick=\{[^{}]*onNavigate\('\/student\/courses'\)[^{}]*\}[\s\S]*?Mata Kuliah/)
    assert.match(weekFile, /onClick=\{[^{}]*onNavigate\('\/student\/course'\)[^{}]*\}[\s\S]*?Keamanan Siber/)
    assert.match(weekFile, /<span className=\{styles\.breadcrumbCurrent\}>Minggu 03<\/span>/)
  })

  test('DashboardPage links primary course card to /course-plan', () => {
    const file = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/dashboard/DashboardPage.tsx'),
      'utf8'
    )
    assert.match(file, /onNavigate\('\/course-plan'\)/)
  })
})

describe('Mobile Responsiveness & Layout Architecture', () => {
  test('index.html specifies viewport meta tag for mobile devices', () => {
    const indexHtml = fs.readFileSync(
      path.resolve(import.meta.dirname, '../index.html'),
      'utf8'
    )
    assert.match(indexHtml, /<meta\s+name="viewport"\s+content="width=device-width,\s*initial-scale=1\.0"\s*\/?>/)
  })

  test('global.css prevents horizontal overflow and enforces iOS input zoom safeguard', () => {
    const globalCss = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/styles/global.css'),
      'utf8'
    )
    assert.match(globalCss, /overflow-x:\s*hidden/)
    assert.match(globalCss, /@media\s*\(max-width:\s*640px\)/)
    assert.match(globalCss, /font-size:\s*16px\s*!important/)
  })

  test('AppNavbar.module.css provides responsive breakpoints for tablet and mobile', () => {
    const navbarCss = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/components/layout/AppNavbar.module.css'),
      'utf8'
    )
    assert.match(navbarCss, /@media\s*\(max-width:\s*768px\)/)
    assert.match(navbarCss, /@media\s*\(max-width:\s*480px\)/)
    assert.match(navbarCss, /\.userName\s*\{\s*display:\s*none;?\s*\}/)
  })

  test('ModalShell.module.css provides responsive mobile dialogs and stacked full-width actions', () => {
    const modalCss = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/components/ui/ModalShell.module.css'),
      'utf8'
    )
    assert.match(modalCss, /@media\s*\(max-width:\s*640px\)/)
    assert.match(modalCss, /flex-direction:\s*column-reverse\s*!important/)
    assert.match(modalCss, /width:\s*100%\s*!important/)
  })

  test('Toast.module.css provides responsive full-width bounds on mobile screens', () => {
    const toastCss = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/components/ui/Toast.module.css'),
      'utf8'
    )
    assert.match(toastCss, /@media\s*\(max-width:\s*640px\)/)
    assert.match(toastCss, /left:\s*16px/)
    assert.match(toastCss, /right:\s*16px/)
  })

  test('all feature page stylesheets contain responsive single-column mobile rules', () => {
    const dashboardCss = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/dashboard/DashboardPage.module.css'),
      'utf8'
    )
    assert.match(dashboardCss, /grid-template-columns:\s*1fr/)

    const coursePlanCss = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/course-plan/CoursePlanPage.module.css'),
      'utf8'
    )
    assert.match(coursePlanCss, /grid-template-columns:\s*1fr/)

    const rpsCss = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/rps/RpsAnalysisPage.module.css'),
      'utf8'
    )
    assert.match(rpsCss, /grid-template-columns:\s*1fr/)

    const weekCss = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/weekly-content/WeekDetailPage.module.css'),
      'utf8'
    )
    assert.match(weekCss, /grid-template-columns:\s*1fr/)

    const studentCss = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/student/Student.module.css'),
      'utf8'
    )
    assert.match(studentCss, /grid-template-columns:\s*1fr/)

    const loginCss = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/auth/LoginPage.module.css'),
      'utf8'
    )
    assert.match(loginCss, /flex-direction:\s*column/)
  })
})


