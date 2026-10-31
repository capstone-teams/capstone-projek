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

/**
 * Identitas & role resmi dari backend (GET /auth/me).
 * Data situs dan perizinan kursus Moodle digabungkan secara graceful jika tersedia.
 */
function buildSession(me, moodle = null) {
  const fullname = moodle?.user?.fullname || `${me.firstname ?? ''} ${me.lastname ?? ''}`.trim() || me.username;
  const role = backendAuth.toUiRole(me.role);
  return {
    site: moodle?.site ?? { name: 'Moodle ITK' },
    user: {
      id: moodle?.user?.id ?? me.id,
      backendId: me.id,
      username: me.username,
      firstname: me.firstname,
      lastname: me.lastname,
      fullname,
      email: me.email,
      avatar: moodle?.user?.avatar ?? null,
      role,
      isAdmin: me.role === 'ADMIN' || !!moodle?.user?.isAdmin,
      teacherCourseIds: moodle?.user?.teacherCourseIds ?? (role === 'dosen' ? [2, 3, 4] : []),
    },
  };
}

/**
 * Autentikasi aplikasi berpusat pada Backend API (Single Gateway).
 * Keberhasilan login dan pemulihan sesi murni ditentukan oleh backend (POST /auth/login & GET /auth/me).
 * Koneksi ke Moodle Web Service bersifat pendukung (graceful) agar kegagalan Moodle tidak membatalkan login.
 */
export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [initializing, setInitializing] = useState(() => backendAuth.hasToken());
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

    // Token Moodle kedaluwarsa tidak mematikan sesi backend, hanya membersihkan token Moodle lokal.
    onMoodleTokenInvalid(() => {
      setMoodleToken(null);
      storeToken(null);
    });
    // 401 dari Backend API menandakan token backend kedaluwarsa -> expire sesi.
    onUnauthorized(expire);

    if (backendAuth.hasToken()) {
      const moodleToken = readStoredToken();
      if (moodleToken) setMoodleToken(moodleToken);

      backendAuth.getCurrentUser()
        .then(async (me) => {
          if (!isCurrent()) return;
          let moodle = null;
          if (moodleToken) {
            try {
              moodle = await resolveSession();
            } catch {
              setMoodleToken(null);
              storeToken(null);
            }
          }
          if (isCurrent()) {
            setSession(buildSession(me, moodle));
          }
        })
        .catch((e) => {
          if (!isCurrent()) return;
          if (isTransient(e)) {
            setSessionNotice(SESSION_NOTICE.UNAVAILABLE);
          } else {
            expire();
          }
        })
        .finally(() => { if (isCurrent()) setInitializing(false); });
    } else if (readStoredToken()) {
      // Tidak ada token backend: pastikan storage Moodle bersih jika ada residu lama.
      storeToken(null);
      setMoodleToken(null);
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

    // 1. Backend Login: otoritas tunggal autentikasi (kontrak design-api §5.1)
    await backendAuth.login(username, password, { isCurrent });
    ensureCurrent();

    const me = await backendAuth.getCurrentUser();
    ensureCurrent();

    // 2. Hubungkan Moodle secara non-blocking / graceful jika tersedia
    let moodle = null;
    try {
      const token = await requestToken(me.username, password);
      ensureCurrent();
      setMoodleToken(token);
      moodle = await resolveSession();
      ensureCurrent();
      storeToken(token);
    } catch {
      // Kegagalan Moodle (server offline atau beda akun) TIDAK membatalkan autentikasi backend
      setMoodleToken(null);
      storeToken(null);
    }

    ensureCurrent();
    const nextSession = buildSession(me, moodle);
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
