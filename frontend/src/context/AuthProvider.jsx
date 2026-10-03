import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  const generation = useRef(0);

  const logout = useCallback(() => {
    generation.current += 1;
    setMoodleToken(null);
    storeToken(null);
    backendAuth.logout();
    setSession(null);
    setInitializing(false);
  }, []);

  useEffect(() => {
    const id = ++generation.current;
    const isCurrent = () => id === generation.current;
    onMoodleTokenInvalid(logout);
    const token = readStoredToken();
    if (token) {
      setMoodleToken(token);
      resolveSession()
        .then((next) => { if (isCurrent()) setSession(next); })
        .catch(() => { if (isCurrent()) logout(); })
        .finally(() => { if (isCurrent()) setInitializing(false); });
    }
    return () => {
      generation.current += 1;
      onMoodleTokenInvalid(null);
    };
  }, [logout]);

  const login = useCallback(async (username, password) => {
    const id = ++generation.current;
    const isCurrent = () => id === generation.current;
    const ensureCurrent = () => {
      if (!isCurrent()) throw new DOMException('Permintaan login tidak lagi aktif.', 'AbortError');
    };
    const token = await requestToken(username, password);
    ensureCurrent();
    setMoodleToken(token);
    let next;
    try {
      next = await resolveSession();
    } catch (e) {
      if (isCurrent()) setMoodleToken(null);
      throw e;
    }
    ensureCurrent();
    storeToken(token);
    setSession(next);
    setInitializing(false);

    // Fitur Generator AI memakai backend capstone; kegagalannya tidak menghalangi akses Moodle.
    if (next.user.role === 'dosen') {
      backendAuth.login(username, password, { isCurrent }).catch(() => {});
    }
    return next;
  }, []);

  const value = useMemo(
    () => ({ session, user: session?.user ?? null, site: session?.site ?? null, initializing, login, logout }),
    [session, initializing, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
