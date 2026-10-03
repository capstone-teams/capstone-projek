import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { ForbiddenPage } from '../pages/StatusPage';
import { Spinner } from './ui';

/** Melindungi route: wajib login Moodle, dan opsional membatasi peran (dosen/mahasiswa). */
export default function RequireAuth({ roles }) {
  const { user, initializing } = useAuth();
  const location = useLocation();

  if (initializing) {
    return (
      <div className="grid min-h-screen place-items-center">
        <Spinner label="Menghubungkan ke Moodle…" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (roles && !roles.includes(user.role)) return <ForbiddenPage />;
  return <Outlet />;
}
