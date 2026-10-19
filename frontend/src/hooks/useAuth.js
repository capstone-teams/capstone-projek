import { useContext } from 'react';
import { AuthContext } from '../context/authContext';

/** { session, user, site, status, isAuthenticated, initializing, sessionNotice, backendError, login, logout } dari AuthProvider. */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth harus dipakai di dalam <AuthProvider>.');
  return ctx;
}
