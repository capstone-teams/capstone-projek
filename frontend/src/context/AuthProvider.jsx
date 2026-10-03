import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AuthContext } from './authContext';
import * as authService from '../services/authService';
import { getToken, setToken, onUnauthorized } from '../services/apiClient';

function normalizeUser(user) {
  const role = { instructor: 'dosen', student: 'mahasiswa' }[user.role] ?? user.role;
  const name = user.name ?? [user.firstname, user.lastname].filter(Boolean).join(' ');
  return { ...user, role, name };
}

/** Rakha's provider/session pattern, adapted to the documented Backend boundary. */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(() => Boolean(getToken()));
  const generation = useRef(0);
  const logout = useCallback(() => {
    generation.current++;
    authService.logout();
    setUser(null);
    setInitializing(false);
  }, []);
  useEffect(() => {
    let active = true;
    const epoch = generation.current;
    onUnauthorized(logout);
    if (getToken()) {
      authService.getCurrentUser().then((next) => {
        if (active && epoch === generation.current) setUser(normalizeUser(next));
      }).catch(() => {
        if (active && epoch === generation.current) logout();
      }).finally(() => { if (active && epoch === generation.current) setInitializing(false); });
    }
    return () => { active = false; onUnauthorized(null); };
  }, [logout]);
  const login = useCallback(async (username, password) => {
    const epoch = ++generation.current;
    const session = await authService.login(username.trim(), password);
    if (epoch !== generation.current) throw new Error('Login dibatalkan.');
    setToken(session.access_token);
    try {
      const next = normalizeUser(await authService.getCurrentUser());
      if (epoch !== generation.current) throw new Error('Login dibatalkan.');
      setUser(next);
      setInitializing(false);
      return next;
    } catch (error) {
      if (epoch === generation.current) logout();
      throw error;
    }
  }, [logout]);
  const value = useMemo(() => ({ user, initializing, login, logout }), [user, initializing, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
