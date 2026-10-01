import { createContext } from 'react'
import type { AuthErrorInfo, AuthState, AuthUser, LoginCredentials, UserProfile } from '../../types/auth'

export interface AuthContextValue extends AuthState {
  isAuthenticated: boolean
  isSubmitting: boolean
  error: AuthErrorInfo | null
  login: (credentials: LoginCredentials) => Promise<AuthUser | null>
  loginWithGoogle: (email: string) => Promise<AuthUser | null>
  loginWithGoogleIdToken: (idToken: string) => Promise<AuthUser | null>
  requestPasswordReset: (identifier: string) => Promise<boolean>
  logout: () => Promise<void>
  updateProfile: (changes: Partial<UserProfile>) => void
  clearError: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
