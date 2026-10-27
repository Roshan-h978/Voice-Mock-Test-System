import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { History, LayoutDashboard, User } from 'lucide-react';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';

const NAV_ITEMS = [
  { to: '/student', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/student/history', label: 'My results', icon: History },
  { to: '/student/profile', label: 'Profile', icon: User },
];

/** Student area: sidebar + top bar around the student pages. */
export default function StudentLayout() {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className={`vmt-shell${navOpen ? ' is-nav-open' : ''}`}>
      <Sidebar items={NAV_ITEMS} roleLabel="Student" homePath="/student" onNavigate={() => setNavOpen(false)} />
      <div className="vmt-drawer-backdrop" onClick={() => setNavOpen(false)} aria-hidden="true" />
      <div className="vmt-app">
        <Navbar variant="app" onMenuClick={() => setNavOpen(true)} profilePath="/student/profile" />
        <main className="vmt-main" id="main">
          <div className="vmt-container">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
