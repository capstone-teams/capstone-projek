import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { ServiceStatus } from '../services/ServiceStatus';
export default function RequireAuth() {
  const { user, initializing } = useAuth();
  const location = useLocation();
  if (initializing) return <ServiceStatus />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return <Outlet />;
}
