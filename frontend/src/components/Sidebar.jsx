import { LogOut, X } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { initials } from '../utils/formatters';
import Brand from './Brand';

/**
 * Navy side navigation. On small screens it slides in as a drawer (opened from the top bar).
 * items: [{ to, label, icon, end?, count? }]
 */
export default function Sidebar({ items, roleLabel, homePath, onNavigate }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleSignOut = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <aside id="app-sidebar" className="vmt-sidebar" aria-label="Main navigation">
      <div className="vmt-sidebar-head">
        <Brand to={homePath} subtitle={roleLabel} />
        <button type="button" className="vmt-icon-btn vmt-icon-btn-sm vmt-sidebar-close" onClick={onNavigate} aria-label="Close menu">
          <X className="vmt-icon" aria-hidden="true" />
        </button>
      </div>

      <nav className="vmt-nav">
        {items.map(({ to, label, icon: Icon, end, count }) => (
          <NavLink key={to} to={to} end={end} className="vmt-nav-item" onClick={onNavigate}>
            <Icon className="vmt-icon" aria-hidden="true" />
            <span>{label}</span>
            {count > 0 && (
              <span className="vmt-nav-count" aria-label={`${count} waiting`}>
                {count}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {user && (
        <div className="vmt-sidebar-foot">
          <span className="vmt-avatar vmt-avatar-sm" aria-hidden="true">
            {initials(user.full_name)}
          </span>
          <div className="vmt-person-text">
            <span className="label">{user.full_name}</span>
            <span className="caption" style={{ color: 'var(--on-navy-muted)' }}>
              {user.email}
            </span>
          </div>
          <button type="button" className="vmt-icon-btn vmt-icon-btn-sm" onClick={handleSignOut} aria-label="Sign out" title="Sign out">
            <LogOut className="vmt-icon" aria-hidden="true" />
          </button>
        </div>
      )}
    </aside>
  );
}
