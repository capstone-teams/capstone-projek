import { useCallback, useMemo, useState, type ReactNode } from 'react'
import type { AuthErrorInfo, AuthUser, LoginCredentials, UserProfile } from '../../types/auth'
import {
  AuthError,
  authService as defaultAuthService,
  type AuthService,
} from '../../services/authService'
import { AuthContext, type AuthContextValue } from './authContext'

interface AuthProviderProps {
  children: ReactNode
  service?: AuthService
}

export function AuthProvider({ children, service = defaultAuthService }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(() => service.getCurrentUser())
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<AuthErrorInfo | null>(null)

  // Runs an auth request with shared submitting/error handling; resolves null on failure.
  const run = useCallback(async <T,>(request: () => Promise<T>): Promise<T | null> => {
    setIsSubmitting(true)
    setError(null)
    try {
      return await request()
    } catch (err) {
      setError(
        err instanceof AuthError
          ? { message: err.message, field: err.field }
          : { message: 'Gagal masuk. Silakan coba lagi.', field: null },
      )
      return null
    } finally {
      setIsSubmitting(false)
    }
  }, [])

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      const signedIn = await run(() => service.login(credentials))
      if (signedIn) setUser(signedIn)
      return signedIn
    },
    [run, service],
  )

  const loginWithGoogle = useCallback(
    async (email: string) => {
      const signedIn = await run(() => service.loginWithGoogle(email))
      if (signedIn) setUser(signedIn)
      return signedIn
    },
    [run, service],
  )

  const loginWithGoogleIdToken = useCallback(
    async (idToken: string) => {
      const signedIn = await run(() => service.loginWithGoogleIdToken(idToken))
      if (signedIn) setUser(signedIn)
      return signedIn
    },
    [run, service],
  )

  const requestPasswordReset = useCallback(
    async (identifier: string) =>
      (await run(() => service.requestPasswordReset(identifier).then(() => true))) ?? false,
    [run, service],
  )

  const logout = useCallback(async () => {
    await service.logout()
    setUser(null)
    setError(null)
  }, [service])

  const updateProfile = useCallback(
    (changes: Partial<UserProfile>) => {
      const updated = service.updateProfile(changes)
      if (updated) setUser(updated)
    },
    [service],
  )

  const clearError = useCallback(() => setError(null), [])

  const value = useMemo<AuthContextValue>(
    () => ({
      status: user ? 'authenticated' : 'unauthenticated',
      user,
      isAuthenticated: user !== null,
      isSubmitting,
      error,
      login,
      loginWithGoogle,
      loginWithGoogleIdToken,
      requestPasswordReset,
      logout,
      updateProfile,
      clearError,
    }),
    [
      user,
      isSubmitting,
      error,
      login,
      loginWithGoogle,
      loginWithGoogleIdToken,
      requestPasswordReset,
      logout,
      updateProfile,
      clearError,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
