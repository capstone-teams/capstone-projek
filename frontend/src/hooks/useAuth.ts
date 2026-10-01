import { useContext } from 'react'
import { AuthContext, type AuthContextValue } from '../features/auth/authContext'

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth harus dipanggil di dalam <AuthProvider>.')
  }
  return context
}
