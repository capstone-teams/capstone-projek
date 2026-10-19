import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AuthContext } from './authContext';
import { onMoodleTokenInvalid, requestToken, setMoodleToken } from '../services/moodle/moodleClient';
import { resolveSession } from '../services/moodle/moodleApi';
import { ApiError, onUnauthorized } from '../services/apiClient';
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

// Backend tidak terjangkau atau error server: token mungkin masih berlaku, jadi jangan dihapus.
function isTransient(error) {
  return error instanceof ApiError && (error.status === 0 || error.status >= 500);
}

// Tandai kegagalan langkah Moodle agar halaman login dapat membedakannya dari error backend.
function fromMoodle(error) {
  if (error && typeof error === 'object') error.source = 'moodle';
  return error;
}

/** Identitas & role dari backend (GET /auth/me); data kursus dan hak mengajar dari Moodle. */
function buildSession(moodle, me) {
  return {
    site: moodle.site,
    user: { ...moodle.user, role: backendAuth.toUiRole(me.role), backendId: me.id, email: me.email },
  };
}

/**
 * Sesi login memakai akun backend (POST /auth/login, dipulihkan via GET /auth/me) dan
 * akun Moodle dengan kredensial yang sama, karena halaman kursus membaca data dari Moodle.
 * Keduanya wajib: kegagalan salah satunya membatalkan login.
 */
export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [initializing, setInitializing] = useState(() => !!readStoredToken() && backendAuth.hasToken());
  // Alasan sesi berakhir di luar kehendak user (mis. token kedaluwarsa), untuk halaman login.
  const [sessionNotice, setSessionNotice] = useState(null);
  const generation = useRef(0);

  const logout = useCallback(() => {
    generation.current += 1;
    setMoodleToken(null);
    storeToken(null);
    backendAuth.logout();
    setSession(null);
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
    onUnauthorized(expire);
    const token = readStoredToken();
    if (token && backendAuth.hasToken()) {
      setMoodleToken(token);
      Promise.all([backendAuth.getCurrentUser(), resolveSession()])
        .then(([me, next]) => { if (isCurrent()) setSession(buildSession(next, me)); })
        .catch((e) => {
          if (!isCurrent()) return;
          if (isTransient(e)) {
            setMoodleToken(null);
            setSessionNotice(SESSION_NOTICE.UNAVAILABLE);
          } else {
            expire();
          }
        })
        .finally(() => { if (isCurrent()) setInitializing(false); });
    } else if (token || backendAuth.hasToken()) {
      // Sesi tidak lengkap (mis. hanya login Moodle dari versi sebelumnya): buang, mulai dari login.
      storeToken(null);
      backendAuth.logout();
    }
    return () => {
      generation.current += 1;
      onMoodleTokenInvalid(null);
      onUnauthorized(null);
    };
  }, [expire]);

  const login = useCallback(async (username, password) => {
    const id = ++generation.current;
    const isCurrent = () => id === generation.current;
    const ensureCurrent = () => {
      if (!isCurrent()) throw new DOMException('Permintaan login tidak lagi aktif.', 'AbortError');
    };
    await backendAuth.login(username, password, { isCurrent });
    ensureCurrent();
    let me, token, next;
    try {
      me = await backendAuth.getCurrentUser();
      ensureCurrent();
      // Username dari backend dipakai untuk Moodle, sehingga login memakai email tetap berhasil.
      token = await requestToken(me.username, password).catch((e) => { throw fromMoodle(e); });
      ensureCurrent();
      setMoodleToken(token);
      next = await resolveSession().catch((e) => { throw fromMoodle(e); });
      ensureCurrent();
    } catch (e) {
      if (isCurrent()) {
        setMoodleToken(null);
        backendAuth.logout();
      }
      throw e;
    }
    storeToken(token);
    const nextSession = buildSession(next, me);
    setSession(nextSession);
    setSessionNotice(null);
    setInitializing(false);
    return nextSession;
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
      login,
      logout,
    }),
    [session, status, initializing, sessionNotice, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
