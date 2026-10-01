import type { AuthUser, LoginCredentials, LoginField, UserProfile, UserRole } from '../types/auth.ts'
import { DOSEN_PROFILE, MAHASISWA_PROFILE } from '../types/auth.ts'

/**
 * Kontrak layanan autentikasi. Implementasi mock di bawah dapat diganti
 * dengan implementasi yang memanggil endpoint `/auth` backend tanpa
 * mengubah AuthProvider.
 */
export interface AuthService {
  login(credentials: LoginCredentials): Promise<AuthUser>
  /** Mock: masuk dengan memilih salah satu akun Google demo. */
  loginWithGoogle(email: string): Promise<AuthUser>
  /** Masuk dengan ID token dari Google Identity Services. */
  loginWithGoogleIdToken(idToken: string): Promise<AuthUser>
  requestPasswordReset(identifier: string): Promise<void>
  logout(): Promise<void>
  getCurrentUser(): AuthUser | null
  updateProfile(profile: Partial<UserProfile>): AuthUser | null
}

export class AuthError extends Error {
  readonly field: LoginField | null

  constructor(message: string, field: LoginField | null = null) {
    super(message)
    this.name = 'AuthError'
    this.field = field
  }
}

/** Subset of the Web Storage API, so tests can pass an in-memory store. */
export interface SessionStorageLike {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

export const AUTH_STORAGE_KEY = 'agentic-lms.auth.user'

/** Kata sandi demo yang berlaku untuk semua akun mock. */
export const MOCK_PASSWORD = 'password123'

export const MOCK_USERS: Record<UserRole, AuthUser> = {
  INSTRUCTOR: {
    id: 'mock-instructor-1',
    username: 'dosen',
    role: 'INSTRUCTOR',
    profile: DOSEN_PROFILE,
  },
  STUDENT: {
    id: 'mock-student-1',
    username: 'mahasiswa',
    role: 'STUDENT',
    profile: MAHASISWA_PROFILE,
  },
}

/**
 * Menentukan role dari username demo: mengandung "mahasiswa" → STUDENT,
 * mengandung "dosen" → INSTRUCTOR. Selain itu tidak dikenali.
 */
export function detectRoleFromUsername(username: string): UserRole | null {
  const cleanUsername = username.trim().toLowerCase()
  if (cleanUsername.includes('mahasiswa')) return 'STUDENT'
  if (cleanUsername.includes('dosen')) return 'INSTRUCTOR'
  return null
}

/**
 * Menentukan role dari email akun Google ITK:
 * `@student.itk.ac.id` → STUDENT, `@itk.ac.id` → INSTRUCTOR.
 */
export function detectRoleFromEmail(email: string): UserRole | null {
  const cleanEmail = email.trim().toLowerCase()
  if (cleanEmail.endsWith('@student.itk.ac.id')) return 'STUDENT'
  if (cleanEmail.endsWith('@itk.ac.id')) return 'INSTRUCTOR'
  return null
}

export function getInitials(name: string): string {
  return (
    name
      .split(' ')
      .map((part) => part[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase() || '?'
  )
}

/** Klaim ID token Google yang dipakai frontend. */
export interface GoogleIdTokenClaims {
  sub: string
  email: string
  email_verified?: boolean
  name?: string
  picture?: string
  exp?: number
}

/**
 * Membaca payload ID token (JWT) Google. Tanda tangan TIDAK diverifikasi di sini;
 * verifikasi harus dilakukan backend sebelum dipakai di produksi.
 */
export function decodeGoogleIdToken(idToken: string): GoogleIdTokenClaims | null {
  const payload = idToken.split('.')[1]
  if (!payload) return null
  try {
    const base64 = payload
      .replace(/-/g, '+')
      .replace(/_/g, '/')
      .padEnd(Math.ceil(payload.length / 4) * 4, '=')
    const bytes = Uint8Array.from(atob(base64), (char) => char.charCodeAt(0))
    const claims: unknown = JSON.parse(new TextDecoder().decode(bytes))
    if (
      claims &&
      typeof claims === 'object' &&
      typeof (claims as GoogleIdTokenClaims).sub === 'string' &&
      typeof (claims as GoogleIdTokenClaims).email === 'string'
    ) {
      return claims as GoogleIdTokenClaims
    }
    return null
  } catch {
    return null
  }
}

const NON_ITK_GOOGLE_ACCOUNT_MESSAGE =
  'Gunakan akun Google dengan email ITK (@itk.ac.id atau @student.itk.ac.id).'

function getBrowserStorage(): SessionStorageLike | null {
  try {
    return typeof window !== 'undefined' ? window.localStorage : null
  } catch {
    return null
  }
}

function isAuthUser(value: unknown): value is AuthUser {
  if (!value || typeof value !== 'object') return false
  const user = value as Partial<AuthUser>
  return (
    typeof user.id === 'string' &&
    typeof user.username === 'string' &&
    (user.role === 'INSTRUCTOR' || user.role === 'STUDENT') &&
    !!user.profile &&
    typeof user.profile === 'object'
  )
}

export function createMockAuthService(
  storage: SessionStorageLike | null = getBrowserStorage(),
  latencyMs = 0,
): AuthService {
  const wait = () =>
    latencyMs > 0 ? new Promise<void>((resolve) => setTimeout(resolve, latencyMs)) : Promise.resolve()

  const read = (): AuthUser | null => {
    try {
      const raw = storage?.getItem(AUTH_STORAGE_KEY)
      if (!raw) return null
      const parsed: unknown = JSON.parse(raw)
      return isAuthUser(parsed) ? parsed : null
    } catch {
      return null
    }
  }

  let current: AuthUser | null = read()

  const write = (user: AuthUser | null) => {
    current = user
    try {
      if (user) storage?.setItem(AUTH_STORAGE_KEY, JSON.stringify(user))
      else storage?.removeItem(AUTH_STORAGE_KEY)
    } catch {
      // Storage unavailable (private mode, blocked site data): keep the session in memory only.
    }
  }

  const signIn = (role: UserRole, username: string): AuthUser => {
    const user: AuthUser = { ...MOCK_USERS[role], username }
    write(user)
    return user
  }

  return {
    async login({ username, password }) {
      await wait()
      const cleanUsername = username.trim()
      if (!cleanUsername) {
        throw new AuthError('Username wajib diisi.', 'username')
      }
      const role = detectRoleFromUsername(cleanUsername)
      if (!role) {
        throw new AuthError(
          `Username "${cleanUsername}" tidak terdaftar. Gunakan "dosen" atau "mahasiswa".`,
          'username',
        )
      }
      if (!password) {
        throw new AuthError('Kata sandi wajib diisi.', 'password')
      }
      if (password !== MOCK_PASSWORD) {
        throw new AuthError('Kata sandi salah. Silakan coba lagi.', 'password')
      }
      return signIn(role, cleanUsername)
    },

    async loginWithGoogle(email) {
      await wait()
      const role = detectRoleFromEmail(email)
      if (!role) {
        throw new AuthError(NON_ITK_GOOGLE_ACCOUNT_MESSAGE)
      }
      return signIn(role, email.trim().toLowerCase())
    },

    async loginWithGoogleIdToken(idToken) {
      const claims = decodeGoogleIdToken(idToken)
      if (!claims) {
        throw new AuthError('Respons Google tidak valid. Silakan coba lagi.')
      }
      if (claims.exp !== undefined && claims.exp * 1000 < Date.now()) {
        throw new AuthError('Sesi Google sudah kedaluwarsa. Silakan coba lagi.')
      }
      if (claims.email_verified === false) {
        throw new AuthError('Email akun Google belum terverifikasi.')
      }
      const email = claims.email.toLowerCase()
      const role = detectRoleFromEmail(email)
      if (!role) {
        throw new AuthError(NON_ITK_GOOGLE_ACCOUNT_MESSAGE)
      }

      const name = claims.name?.trim() || email
      const baseProfile = MOCK_USERS[role].profile
      const user: AuthUser = {
        id: `google-${claims.sub}`,
        username: email,
        role,
        profile: {
          ...baseProfile,
          name,
          email,
          avatarInitial: getInitials(name),
          // NIM mahasiswa = bagian lokal email ITK; NIP dosen belum tersedia tanpa backend.
          identifier: role === 'STUDENT' ? email.split('@')[0] : '',
        },
      }
      write(user)
      return user
    },

    async requestPasswordReset(identifier) {
      await wait()
      if (!identifier.trim()) {
        throw new AuthError('Username atau email wajib diisi.', 'username')
      }
      // Mock: tidak ada email yang benar-benar dikirim.
    },

    async logout() {
      await wait()
      write(null)
    },

    getCurrentUser() {
      return current
    },

    updateProfile(changes) {
      if (!current) return null
      const updated: AuthUser = { ...current, profile: { ...current.profile, ...changes } }
      write(updated)
      return updated
    },
  }
}

export const authService: AuthService = createMockAuthService()
