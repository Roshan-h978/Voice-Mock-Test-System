import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { homeFor } from '../utils/constants';
import LoadingSpinner from './LoadingSpinner';

/** Only signed-in users with the right role (student or admin) see the children. */
export default function ProtectedRoute({ role, children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingSpinner fullScreen label="Loading your account…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (role && user.role !== role) return <Navigate to={homeFor(user)} replace />;
  return children;
}

/** Sign-in and sign-up pages: signed-in users go straight to their dashboard. */
export function GuestRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingSpinner fullScreen label="Loading…" />;
  if (user) return <Navigate to={homeFor(user, location.state?.from?.pathname)} replace />;
  return children;
}
