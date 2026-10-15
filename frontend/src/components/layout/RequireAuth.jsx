import { Navigate, Outlet, useLocation, useOutletContext } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { ForbiddenPage } from '../../pages/StatusPage';
import { Spinner } from '../ui';

/** Melindungi route: wajib login Moodle, dan opsional membatasi peran (dosen/mahasiswa). */
export default function RequireAuth({ roles }) {
  const { user, initializing } = useAuth();
  const location = useLocation();
  // Diteruskan agar route bersarang (mis. tab AI di kursus) tetap menerima context layout induk.
  const parentContext = useOutletContext();

  if (initializing) {
    return (
      <div className="grid min-h-screen place-items-center">
        <Spinner label="Menghubungkan ke Moodle…" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (roles && !roles.includes(user.role)) return <ForbiddenPage />;
  return <Outlet context={parentContext} />;
}
