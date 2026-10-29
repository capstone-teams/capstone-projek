import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { onForbidden } from '../../services/apiClient';
import { useLatest } from '../../hooks/useLatest';
import { ForbiddenPage } from '../../pages/StatusPage';
import AppStatus from './AppStatus';
import ApplicationHeader from './ApplicationHeader';

export default function MoodleLayout() {
  const { pathname } = useLocation();
  const currentPath = useLatest(pathname);
  // Halaman yang ditolak backend (403 AUTHORIZATION_DENIED); berpindah halaman menghapusnya.
  const [deniedPath, setDeniedPath] = useState(null);

  useEffect(() => {
    onForbidden(() => setDeniedPath(currentPath.current));
    return () => onForbidden(null);
  }, [currentPath]);

  return (
    <div className="approved-app">
      <ApplicationHeader />
      <AppStatus />
      {deniedPath === pathname ? <ForbiddenPage /> : <Outlet />}
    </div>
  );
}

export function PageContainer({ children }) {
  return <main className="approved-page">{children}</main>;
}
