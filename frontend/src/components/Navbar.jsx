import { LayoutDashboard, Menu } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ROLE_HOME } from '../utils/constants';
import { initials } from '../utils/formatters';
import Brand from './Brand';
import Button from './Button';

const todayFormat = new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });

/**
 * variant="public": top bar of the landing page (brand + sign-in links).
 * variant="app": top bar inside the student/admin area (menu button on small screens + user).
 */
export default function Navbar({ variant = 'public', onMenuClick, profilePath }) {
  const { user } = useAuth();

  if (variant === 'app') {
    return (
      <header className="vmt-topbar">
        <div className="vmt-topbar-left">
          <button
            type="button"
            className="vmt-icon-btn vmt-menu-btn"
            onClick={onMenuClick}
            aria-label="Open menu"
            aria-controls="app-sidebar"
          >
            <Menu className="vmt-icon" aria-hidden="true" />
          </button>
          <span className="body-sm vmt-muted">{todayFormat.format(new Date())}</span>
        </div>
        {user && (
          <Link to={profilePath} className="vmt-topbar-right vmt-person" style={{ textDecoration: 'none' }} aria-label="Open my profile">
            <span className="vmt-person-text vmt-hide-sm" style={{ textAlign: 'right' }}>
              <span className="label">{user.full_name}</span>
              <span className="caption vmt-muted">{user.email}</span>
            </span>
            <span className="vmt-avatar" aria-hidden="true">
              {initials(user.full_name)}
            </span>
          </Link>
        )}
      </header>
    );
  }

  return (
    <header className="vmt-navbar">
      <div className="vmt-navbar-inner">
        <Brand />
        <nav className="vmt-navbar-links" aria-label="Account">
          {user ? (
            <Button to={ROLE_HOME[user.role] || '/'} icon={LayoutDashboard}>
              My dashboard
            </Button>
          ) : (
            <>
              <Button to="/login" variant="ghost">
                Sign in
              </Button>
              <Button to="/register">Create account</Button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
