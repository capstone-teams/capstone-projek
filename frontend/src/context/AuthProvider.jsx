import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AuthContext } from './authContext';
import { onMoodleTokenInvalid, requestToken, setMoodleToken } from '../services/moodle/moodleClient';
import { resolveSession } from '../services/moodle/moodleApi';
import * as backendAuth from '../services/authService';
import { MOODLE_SESSION_KEY } from '../services/config';
import { readJson, writeJson } from '../utils/storage';
import { AUTH_STATUS, SESSION_NOTICE } from '../types/auth';

// Bila localStorage tidak tersedia, sesi hanya hidup selama tab terbuka.
function readStoredToken() {
  const token = readJson(MOODLE_SESSION_KEY)?.token;
  return typeof token === 'string' && token ? token : null;
}

function storeToken(token) {
  writeJson(MOODLE_SESSION_KEY, token ? { token } : null);
}

/**
 * Sesi login memakai akun Moodle (login/token.php).
 * Peran dosen/mahasiswa diturunkan dari hak akses user di course Moodle.
 */
export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [initializing, setInitializing] = useState(() => !!readStoredToken());
  // Alasan sesi berakhir di luar kehendak user (mis. token kedaluwarsa), untuk halaman login.
  const [sessionNotice, setSessionNotice] = useState(null);
  // Kegagalan login backend AI; Moodle tetap dapat dipakai.
  const [backendError, setBackendError] = useState(null);
  const generation = useRef(0);

  const logout = useCallback(() => {
    generation.current += 1;
    setMoodleToken(null);
    storeToken(null);
    backendAuth.logout();
    setSession(null);
    setBackendError(null);
    setSessionNotice(null);
    setInitializing(false);
  }, []);

  const expire = useCallback(() => {
    logout();
    setSessionNotice(SESSION_NOTICE.EXPIRED);
  }, [logout]);

  useEffect(() => {
    const id = ++generation.current;
    const isCurrent = () => id === generation.current;
    onMoodleTokenInvalid(expire);
    const token = readStoredToken();
    if (token) {
      setMoodleToken(token);
      resolveSession()
        .then((next) => { if (isCurrent()) setSession(next); })
        .catch(() => { if (isCurrent()) expire(); })
        .finally(() => { if (isCurrent()) setInitializing(false); });
    }
    return () => {
      generation.current += 1;
      onMoodleTokenInvalid(null);
    };
  }, [expire]);

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
    setSessionNotice(null);
    setBackendError(null);
    setInitializing(false);

    // Fitur Generator AI memakai backend capstone; kegagalannya tidak menghalangi akses Moodle.
    if (next.user.role === 'dosen') {
      backendAuth.login(username, password, { isCurrent }).catch((e) => {
        if (isCurrent()) setBackendError(e);
      });
    }
    return next;
  }, []);

  const status = initializing ? AUTH_STATUS.INITIALIZING : session ? AUTH_STATUS.AUTHENTICATED : AUTH_STATUS.ANONYMOUS;
  const value = useMemo(
    () => ({
      session,
      user: session?.user ?? null,
      site: session?.site ?? null,
      status,
      isAuthenticated: status === AUTH_STATUS.AUTHENTICATED,
      initializing,
      sessionNotice,
      backendError,
      login,
      logout,
    }),
    [session, status, initializing, sessionNotice, backendError, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
