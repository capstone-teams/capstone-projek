import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { ROLE_LABEL, homePathFor } from '../types/auth';

function StatusLayout({ code, title, children }) {
  return (
    <div className="grid min-h-[60vh] place-items-center px-4 py-10">
      <div className="flex max-w-md flex-col items-center gap-3 text-center">
        <span className="text-6xl font-extrabold text-primary">{code}</span>
        <h1 className="text-2xl">{title}</h1>
        {children}
      </div>
    </div>
  );
}

function HomeLink() {
  const { user } = useAuth();
  return (
    <Link to={homePathFor(user?.role)} className="btn btn--primary">
      Ke halaman utama
    </Link>
  );
}

export function NotFoundPage() {
  return (
    <StatusLayout code="404" title="Halaman tidak ditemukan">
      <HomeLink />
    </StatusLayout>
  );
}

/** Ditampilkan untuk akses lewat URL ke halaman role lain dan untuk response 403 AUTHORIZATION_DENIED. */
export function ForbiddenPage() {
  const { user } = useAuth();
  const role = ROLE_LABEL[user?.role];
  return (
    <StatusLayout code="403" title="Akses ditolak">
      <p className="text-muted">
        Anda tidak memiliki izin untuk membuka halaman ini{role ? ` sebagai ${role.toLowerCase()}` : ''}.
      </p>
      <HomeLink />
    </StatusLayout>
  );
}
