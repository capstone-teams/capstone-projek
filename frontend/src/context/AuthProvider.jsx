import { useCallback, useEffect, useMemo, useState } from 'react';
import { AuthContext } from './authContext';
import { onMoodleTokenInvalid, requestToken, setMoodleToken } from '../services/moodle/moodleClient';
import { resolveSession } from '../services/moodle/moodleApi';
import * as backendAuth from '../services/authService';
import { MOODLE_SESSION_KEY } from '../services/config';

function readStoredToken() {
  try {
    return JSON.parse(localStorage.getItem(MOODLE_SESSION_KEY))?.token ?? null;
  } catch {
    return null;
  }
}

function storeToken(token) {
  try {
    if (token) localStorage.setItem(MOODLE_SESSION_KEY, JSON.stringify({ token }));
    else localStorage.removeItem(MOODLE_SESSION_KEY);
  } catch {
    // localStorage tidak tersedia: sesi hanya hidup selama tab terbuka.
  }
}

/**
 * Sesi login memakai akun Moodle (login/token.php).
 * Peran dosen/mahasiswa diturunkan dari hak akses user di course Moodle.
 */
export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [initializing, setInitializing] = useState(() => !!readStoredToken());

  const logout = useCallback(() => {
    setMoodleToken(null);
    storeToken(null);
    backendAuth.logout();
    setSession(null);
  }, []);

  useEffect(() => {
    onMoodleTokenInvalid(logout);
    const token = readStoredToken();
    if (!token) return;
    setMoodleToken(token);
    resolveSession()
      .then(setSession)
      .catch(() => logout())
      .finally(() => setInitializing(false));
  }, [logout]);

  const login = useCallback(async (username, password) => {
    const token = await requestToken(username, password);
    setMoodleToken(token);
    let next;
    try {
      next = await resolveSession();
    } catch (e) {
      setMoodleToken(null);
      throw e;
    }
    storeToken(token);
    setSession(next);

    // Fitur Generator AI memakai backend capstone; kegagalannya tidak menghalangi akses Moodle.
    if (next.user.role === 'dosen') {
      backendAuth.login(username, password).catch(() => {});
    }
    return next;
  }, []);

  const value = useMemo(
    () => ({ session, user: session?.user ?? null, site: session?.site ?? null, initializing, login, logout }),
    [session, initializing, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
