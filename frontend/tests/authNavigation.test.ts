import fs from 'node:fs'
import path from 'node:path'
import { test, describe } from 'node:test'
import assert from 'node:assert/strict'
import type { AppPath } from '../src/types/navigation.ts'
import { APP_ROUTES, ROLE_NAVIGATION } from '../src/types/navigation.ts'
import type { AuthUser } from '../src/types/auth.ts'
import { ROLE_LABELS, USER_ROLES } from '../src/types/auth.ts'
import {
  getNavigationForRole,
  getPostLoginPath,
  isPathAllowedForRole,
  resolveRouteAccess,
} from '../src/utils/navigation.ts'
import {
  AUTH_STORAGE_KEY,
  AuthError,
  MOCK_PASSWORD,
  MOCK_USERS,
  createMockAuthService,
  decodeGoogleIdToken,
  detectRoleFromEmail,
  getInitials,
  detectRoleFromUsername,
  type SessionStorageLike,
} from '../src/services/authService.ts'

function createMemoryStorage(initial: Record<string, string> = {}): SessionStorageLike & {
  data: Map<string, string>
} {
  const data = new Map(Object.entries(initial))
  return {
    data,
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => void data.set(key, value),
    removeItem: (key) => void data.delete(key),
  }
}

const instructor: AuthUser = MOCK_USERS.INSTRUCTOR
const student: AuthUser = MOCK_USERS.STUDENT

describe('User Roles', () => {
  test('defines Instructor and Student roles matching the backend enum', () => {
    assert.deepEqual(Object.values(USER_ROLES).sort(), ['INSTRUCTOR', 'STUDENT'])
    assert.equal(ROLE_LABELS.INSTRUCTOR, 'Dosen')
    assert.equal(ROLE_LABELS.STUDENT, 'Mahasiswa')
  })

  test('mock users carry a profile whose role matches the user role', () => {
    assert.equal(instructor.role, 'INSTRUCTOR')
    assert.equal(instructor.profile.role, 'INSTRUCTOR')
    assert.equal(student.role, 'STUDENT')
    assert.equal(student.profile.role, 'STUDENT')
  })
})

describe('Mock Authentication Service', () => {
  test('detects role from demo username', () => {
    assert.equal(detectRoleFromUsername('dosen'), 'INSTRUCTOR')
    assert.equal(detectRoleFromUsername('  Dosen.ITK '), 'INSTRUCTOR')
    assert.equal(detectRoleFromUsername('mahasiswa'), 'STUDENT')
    assert.equal(detectRoleFromUsername('MAHASISWA01'), 'STUDENT')
    assert.equal(detectRoleFromUsername('admin'), null)
    assert.equal(detectRoleFromUsername(''), null)
  })

  test('starts unauthenticated with empty storage', () => {
    const service = createMockAuthService(createMemoryStorage())
    assert.equal(service.getCurrentUser(), null)
  })

  test('login as dosen returns an instructor and persists the session', async () => {
    const storage = createMemoryStorage()
    const service = createMockAuthService(storage)

    const user = await service.login({ username: 'dosen', password: MOCK_PASSWORD })
    assert.equal(user.role, 'INSTRUCTOR')
    assert.equal(user.username, 'dosen')
    assert.deepEqual(service.getCurrentUser(), user)
    assert.ok(storage.data.has(AUTH_STORAGE_KEY))
  })

  test('login as mahasiswa returns a student', async () => {
    const service = createMockAuthService(createMemoryStorage())
    const user = await service.login({ username: 'mahasiswa', password: MOCK_PASSWORD })
    assert.equal(user.role, 'STUDENT')
    assert.equal(user.profile.name, 'Noel Sipayung')
  })

  test('rejects unknown usernames with an error naming the username', async () => {
    const service = createMockAuthService(createMemoryStorage())
    await assert.rejects(service.login({ username: ' admin ', password: 'x' }), (err) => {
      assert.ok(err instanceof AuthError)
      assert.match(err.message, /Username "admin" tidak terdaftar/)
      return true
    })
    assert.equal(service.getCurrentUser(), null)
  })

  test('rejects a wrong password with an error on the password field', async () => {
    const service = createMockAuthService(createMemoryStorage())
    await assert.rejects(service.login({ username: 'dosen', password: 'salah' }), (err) => {
      assert.ok(err instanceof AuthError)
      assert.equal(err.field, 'password')
      assert.match(err.message, /Kata sandi salah/)
      return true
    })
    assert.equal(service.getCurrentUser(), null)
  })

  test('rejects an empty password', async () => {
    const service = createMockAuthService(createMemoryStorage())
    await assert.rejects(service.login({ username: 'mahasiswa', password: '' }), (err) => {
      assert.ok(err instanceof AuthError)
      assert.equal(err.field, 'password')
      assert.match(err.message, /Kata sandi wajib diisi/)
      return true
    })
  })

  test('reports username errors before password errors', async () => {
    const service = createMockAuthService(createMemoryStorage())
    await assert.rejects(service.login({ username: 'admin', password: 'salah' }), (err) => {
      assert.ok(err instanceof AuthError)
      assert.equal(err.field, 'username')
      return true
    })
  })

  test('rejects an empty username', async () => {
    const service = createMockAuthService(createMemoryStorage())
    await assert.rejects(service.login({ username: '   ', password: 'x' }), /Username wajib diisi/)
  })

  test('logout clears the current user and storage', async () => {
    const storage = createMemoryStorage()
    const service = createMockAuthService(storage)
    await service.login({ username: 'dosen', password: MOCK_PASSWORD })

    await service.logout()
    assert.equal(service.getCurrentUser(), null)
    assert.equal(storage.data.has(AUTH_STORAGE_KEY), false)
  })

  test('restores a persisted session and ignores corrupt storage', () => {
    const restored = createMockAuthService(
      createMemoryStorage({ [AUTH_STORAGE_KEY]: JSON.stringify(student) }),
    )
    assert.deepEqual(restored.getCurrentUser(), student)

    const corrupt = createMockAuthService(createMemoryStorage({ [AUTH_STORAGE_KEY]: '{not json' }))
    assert.equal(corrupt.getCurrentUser(), null)

    const wrongShape = createMockAuthService(
      createMemoryStorage({ [AUTH_STORAGE_KEY]: JSON.stringify({ role: 'ADMIN' }) }),
    )
    assert.equal(wrongShape.getCurrentUser(), null)
  })

  test('works without storage by keeping the session in memory', async () => {
    const service = createMockAuthService(null)
    await service.login({ username: 'dosen', password: MOCK_PASSWORD })
    assert.equal(service.getCurrentUser()?.role, 'INSTRUCTOR')

    const updated = service.updateProfile({ name: 'Dosen Baru' })
    assert.equal(updated?.profile.name, 'Dosen Baru')
    assert.equal(service.getCurrentUser()?.profile.name, 'Dosen Baru')
  })

  test('updateProfile returns null when logged out', () => {
    const service = createMockAuthService(createMemoryStorage())
    assert.equal(service.updateProfile({ name: 'X' }), null)
  })
})

describe('Protected Route Behavior', () => {
  test('redirects unauthenticated visitors of protected routes to /login', () => {
    const protectedPaths: AppPath[] = ['/dashboard', '/course-plan', '/student/courses', '/material-view']
    for (const p of protectedPaths) {
      assert.deepEqual(resolveRouteAccess(p, null), {
        kind: 'redirect',
        path: '/login',
        reason: 'unauthenticated',
      })
    }
  })

  test('allows the login page only for guests', () => {
    assert.deepEqual(resolveRouteAccess('/login', null), { kind: 'allow', path: '/login' })
    assert.deepEqual(resolveRouteAccess('/login', instructor), {
      kind: 'redirect',
      path: '/dashboard',
      reason: 'already-authenticated',
    })
    assert.deepEqual(resolveRouteAccess('/login', student), {
      kind: 'redirect',
      path: '/student/courses',
      reason: 'already-authenticated',
    })
  })

  test('sends users to /unauthorized for routes of another role', () => {
    assert.deepEqual(resolveRouteAccess('/student/week', instructor), {
      kind: 'redirect',
      path: '/unauthorized',
      reason: 'unauthorized',
    })
    assert.deepEqual(resolveRouteAccess('/rps-analysis', student), {
      kind: 'redirect',
      path: '/unauthorized',
      reason: 'unauthorized',
    })
  })

  test('allows each role into its own routes and shared routes', () => {
    for (const route of Object.values(APP_ROUTES)) {
      if (route.access !== 'authenticated') continue
      for (const user of [instructor, student]) {
        const decision = resolveRouteAccess(route.path, user)
        const expected = isPathAllowedForRole(route.path, user.role) ? 'allow' : 'redirect'
        assert.equal(decision.kind, expected, `${user.role} → ${route.path}`)
      }
    }
  })

  test('not-found and unauthorized pages are reachable by anyone', () => {
    for (const user of [null, instructor, student]) {
      assert.equal(resolveRouteAccess('/not-found', user).kind, 'allow')
      assert.equal(resolveRouteAccess('/unauthorized', user).kind, 'allow')
    }
  })

  test('after login, returns to the requested route when the role may open it', () => {
    assert.equal(getPostLoginPath(instructor, '/course-plan'), '/course-plan')
    assert.equal(getPostLoginPath(student, '/student/week'), '/student/week')
    assert.equal(getPostLoginPath(student, '/material-view'), '/material-view')
  })

  test('after login, falls back to the role home otherwise', () => {
    assert.equal(getPostLoginPath(student, '/course-plan'), '/student/courses')
    assert.equal(getPostLoginPath(instructor, '/login'), '/dashboard')
    assert.equal(getPostLoginPath(instructor, '/not-found'), '/dashboard')
    assert.equal(getPostLoginPath(student, null), '/student/courses')
  })
})

describe('Role-Based Navigation', () => {
  test('every role has a non-empty menu', () => {
    assert.ok(getNavigationForRole('INSTRUCTOR').length > 0)
    assert.ok(getNavigationForRole('STUDENT').length > 0)
  })

  test('menu items only point to routes the role may open', () => {
    for (const role of ['INSTRUCTOR', 'STUDENT'] as const) {
      for (const item of ROLE_NAVIGATION[role]) {
        assert.ok(APP_ROUTES[item.path], `${item.path} must be a defined route`)
        assert.equal(
          resolveRouteAccess(item.path, MOCK_USERS[role]).kind,
          'allow',
          `${role} menu item ${item.path} must be accessible`,
        )
      }
    }
  })
})

describe('Google Login & Password Reset (mock)', () => {
  test('detects role from ITK email domain', () => {
    assert.equal(detectRoleFromEmail('chandra.cahyo@itk.ac.id'), 'INSTRUCTOR')
    assert.equal(detectRoleFromEmail('11211045@student.itk.ac.id'), 'STUDENT')
    assert.equal(detectRoleFromEmail('someone@gmail.com'), null)
  })

  test('loginWithGoogle signs in the matching role', async () => {
    const service = createMockAuthService(createMemoryStorage())
    const user = await service.loginWithGoogle(MOCK_USERS.STUDENT.profile.email)
    assert.equal(user.role, 'STUDENT')
    assert.equal(service.getCurrentUser()?.role, 'STUDENT')
  })

  test('loginWithGoogle rejects non-ITK accounts', async () => {
    const service = createMockAuthService(createMemoryStorage())
    await assert.rejects(service.loginWithGoogle('someone@gmail.com'), (err) => {
      assert.ok(err instanceof AuthError)
      assert.equal(err.field, null)
      assert.match(err.message, /email ITK/)
      return true
    })
    assert.equal(service.getCurrentUser(), null)
  })

  test('requestPasswordReset requires a username or email', async () => {
    const service = createMockAuthService(createMemoryStorage())
    await service.requestPasswordReset('dosen')
    await assert.rejects(service.requestPasswordReset('  '), /wajib diisi/)
  })

  test('LoginPage has password visibility toggle, Google login, and forgot password', () => {
    const file = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/auth/LoginPage.tsx'),
      'utf8'
    )
    assert.match(file, /type=\{showPassword \? 'text' : 'password'\}/)
    assert.match(file, /Tampilkan kata sandi/)
    assert.match(file, /Masuk dengan/)
    assert.match(file, /loginWithGoogle\(email\)/)
    assert.match(file, /Lupa kata sandi\?/)
    assert.doesNotMatch(file, /Tutorial Video|Panduan LMS|English/)
  })
})

function fakeGoogleIdToken(claims: Record<string, unknown>): string {
  const encode = (value: unknown) => Buffer.from(JSON.stringify(value)).toString('base64url')
  return `${encode({ alg: 'RS256', typ: 'JWT' })}.${encode(claims)}.signature`
}

describe('Google Identity Services Login', () => {
  const future = Math.floor(Date.now() / 1000) + 3600

  test('decodes a Google ID token payload including UTF-8 names', () => {
    const claims = decodeGoogleIdToken(
      fakeGoogleIdToken({ sub: '123', email: 'a@itk.ac.id', name: 'Ångström Dosen' }),
    )
    assert.equal(claims?.sub, '123')
    assert.equal(claims?.name, 'Ångström Dosen')
  })

  test('rejects malformed tokens', () => {
    assert.equal(decodeGoogleIdToken('not-a-token'), null)
    assert.equal(decodeGoogleIdToken('a.%%%.c'), null)
    assert.equal(decodeGoogleIdToken(fakeGoogleIdToken({ email: 'a@itk.ac.id' })), null)
  })

  test('signs in an ITK instructor with the Google name and email', async () => {
    const service = createMockAuthService(createMemoryStorage())
    const user = await service.loginWithGoogleIdToken(
      fakeGoogleIdToken({
        sub: '42',
        email: 'Budi.Santoso@itk.ac.id',
        email_verified: true,
        name: 'Budi Santoso',
        exp: future,
      }),
    )
    assert.equal(user.id, 'google-42')
    assert.equal(user.role, 'INSTRUCTOR')
    assert.equal(user.profile.email, 'budi.santoso@itk.ac.id')
    assert.equal(user.profile.name, 'Budi Santoso')
    assert.equal(user.profile.avatarInitial, 'BS')
    assert.deepEqual(service.getCurrentUser(), user)
  })

  test('uses the email local part as NIM for students', async () => {
    const service = createMockAuthService(createMemoryStorage())
    const user = await service.loginWithGoogleIdToken(
      fakeGoogleIdToken({ sub: '7', email: '11211099@student.itk.ac.id', name: 'Siti', exp: future }),
    )
    assert.equal(user.role, 'STUDENT')
    assert.equal(user.profile.identifier, '11211099')
  })

  test('rejects non-ITK, unverified, and expired Google accounts', async () => {
    const service = createMockAuthService(createMemoryStorage())
    await assert.rejects(
      service.loginWithGoogleIdToken(fakeGoogleIdToken({ sub: '1', email: 'x@gmail.com', exp: future })),
      /email ITK/,
    )
    await assert.rejects(
      service.loginWithGoogleIdToken(
        fakeGoogleIdToken({ sub: '1', email: 'x@itk.ac.id', email_verified: false, exp: future }),
      ),
      /belum terverifikasi/,
    )
    await assert.rejects(
      service.loginWithGoogleIdToken(fakeGoogleIdToken({ sub: '1', email: 'x@itk.ac.id', exp: 1 })),
      /kedaluwarsa/,
    )
    await assert.rejects(service.loginWithGoogleIdToken('garbage'), /tidak valid/)
    assert.equal(service.getCurrentUser(), null)
  })

  test('getInitials takes the first letters of the first two words', () => {
    assert.equal(getInitials('Muchammad Chandra Cahyo'), 'MC')
    assert.equal(getInitials('noel'), 'N')
    assert.equal(getInitials(''), '?')
  })

  test('LoginPage uses the official Google button only when a client ID is configured', () => {
    const file = fs.readFileSync(
      path.resolve(import.meta.dirname, '../src/features/auth/LoginPage.tsx'),
      'utf8'
    )
    assert.match(file, /GOOGLE_CLIENT_ID \?/)
    assert.match(file, /<GoogleSignInButton/)
    assert.match(file, /isGooglePickerOpen \?/)
  })
})
