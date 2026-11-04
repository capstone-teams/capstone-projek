import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AuthContext } from './authContext';
import { ApiError, onUnauthorized } from '../services/apiClient';
import * as backendAuth from '../services/authService';
import { AUTH_STATUS, ROLE, SESSION_NOTICE } from '../types/auth';

function isTransient(error) {
  return error instanceof ApiError && (error.status === 0 || error.status >= 500);
}

<<<<<<< HEAD
/**
 * Identitas & role resmi dari backend (GET /auth/me).
 * Otoritas tunggal berada pada Backend API (Single Gateway).
 */
function buildSession(me) {
  const fullname = `${me.firstname ?? ''} ${me.lastname ?? ''}`.trim() || me.username;
  const role = backendAuth.toUiRole(me.role);
  const isDosen = role === ROLE.DOSEN || role === 'dosen';
=======
// Tandai kegagalan langkah setelah akun backend terverifikasi, agar halaman login dapat membedakannya.
function fromMoodle(error) {
  if (error && typeof error === 'object') error.source = 'moodle';
  return error;
}

/** Identitas & role dari backend (GET /auth/me); data kursus dan hak mengajar dari layanan LMS (belum ada API backend). */
function buildSession(moodle, me) {
>>>>>>> develop
  return {
    site: { name: 'Moodle ITK' },
    user: {
      id: me.id,
      backendId: me.id,
      username: me.username,
      firstname: me.firstname,
      lastname: me.lastname,
      fullname,
      email: me.email,
      avatar: null,
      role,
      isAdmin: me.role === 'ADMIN',
      teacherCourseIds: isDosen ? [2, 3, 4] : [],
    },
  };
}

<<<<<<< HEAD
=======
/**
 * Sesi login memakai akun backend (POST /auth/login, dipulihkan via GET /auth/me) dan token LMS
 * dengan kredensial yang sama, karena data kursus belum tersedia lewat API backend.
 * Keduanya wajib: kegagalan salah satunya membatalkan login.
 */
>>>>>>> develop
export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [initializing, setInitializing] = useState(() => backendAuth.hasToken());
  // Alasan sesi berakhir di luar kehendak user (mis. token kedaluwarsa), untuk halaman login.
  const [sessionNotice, setSessionNotice] = useState(null);
  const generation = useRef(0);

  const logout = useCallback(() => {
    generation.current += 1;
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

    onUnauthorized(expire);

    if (backendAuth.hasToken()) {
      backendAuth.getCurrentUser()
        .then((me) => {
          if (!isCurrent()) return;
          setSession(buildSession(me));
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
<<<<<<< HEAD
=======
    } else if (token || backendAuth.hasToken()) {
      // Sesi tidak lengkap (mis. tersisa dari versi sebelumnya): buang, mulai dari login.
      storeToken(null);
      backendAuth.logout();
>>>>>>> develop
    }

    return () => {
      generation.current += 1;
      onUnauthorized(null);
    };
  }, [expire]);

  const login = useCallback(async (username, password) => {
    const loginGen = ++generation.current;
    const isCurrent = () => loginGen === generation.current;
    const ensureCurrent = () => {
      if (!isCurrent()) throw new Error('Aksi dibatalkan');
    };

    await backendAuth.login(username, password, { isCurrent });
    ensureCurrent();
<<<<<<< HEAD

    const me = await backendAuth.getCurrentUser();
    ensureCurrent();

    const nextSession = buildSession(me);
=======
    let me, token, next;
    try {
      me = await backendAuth.getCurrentUser();
      ensureCurrent();
      // Username dari backend dipakai untuk token LMS, sehingga login memakai email tetap berhasil.
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
>>>>>>> develop
    setSession(nextSession);
    setSessionNotice(null);
    setInitializing(false);
    return nextSession;
  }, []);

  const value = useMemo(() => {
    const status = initializing
      ? AUTH_STATUS.INITIALIZING
      : session
        ? AUTH_STATUS.AUTHENTICATED
        : AUTH_STATUS.ANONYMOUS;

    return {
      status,
      session,
      user: session?.user ?? null,
      site: session?.site ?? null,
      sessionNotice,
      initializing,
      isAuthenticated: status === AUTH_STATUS.AUTHENTICATED,
      login,
      logout,
      expire,
    };
  }, [initializing, session, sessionNotice, login, logout, expire]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
