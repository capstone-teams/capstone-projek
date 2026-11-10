import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AuthContext } from './authContext';
import { ApiError, onUnauthorized } from '../services/apiClient';
import * as backendAuth from '../services/authService';
import { AUTH_STATUS, ROLE, SESSION_NOTICE } from '../types/auth';

const MOCK_SESSION = import.meta.env.VITE_USE_MOCK === 'true';

function isTransient(error) {
  return error instanceof ApiError && (error.status === 0 || error.status >= 500);
}

/**
 * Identitas & role resmi dari backend (GET /auth/me).
 * Otoritas tunggal berada pada Backend API (Single Gateway).
 */
function buildSession(me) {
  const fullname = `${me.firstname ?? ''} ${me.lastname ?? ''}`.trim() || me.username;
  const role = backendAuth.toUiRole(me.role);
  const isDosen = role === ROLE.DOSEN || role === 'dosen';
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
      // Kursus ajar hanya diketahui pada data mock (kursus 2-4). Lewat Backend Gateway tidak ada data pendaftaran
      // Moodle, jadi dibiarkan kosong (undefined) dan peran pengajar mengikuti role dosen dari backend.
      teacherCourseIds: MOCK_SESSION ? (isDosen ? [2, 3, 4] : []) : undefined,
    },
  };
}

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

    const me = await backendAuth.getCurrentUser();
    ensureCurrent();

    const nextSession = buildSession(me);
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
