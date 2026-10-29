import { Suspense, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Bell, BookOpenCheck, History, LayoutDashboard, Mic, TrendingUp, User } from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import { NotificationProvider, useNotifications } from '../context/NotificationContext';

function StudentShell() {
  const [navOpen, setNavOpen] = useState(false);
  const { unread } = useNotifications();

  const navItems = [
    { to: '/student', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/student/practice', label: 'Quick practice', icon: Mic },
    { to: '/student/progress', label: 'My progress', icon: TrendingUp },
    { to: '/student/notebook', label: 'Mistakes notebook', icon: BookOpenCheck },
    { to: '/student/history', label: 'My results', icon: History },
    { to: '/student/notifications', label: 'Notifications', icon: Bell, count: unread, countLabel: 'unread' },
    { to: '/student/profile', label: 'Profile', icon: User },
  ];

  return (
    <div className={`vmt-shell${navOpen ? ' is-nav-open' : ''}`}>
      <Sidebar items={navItems} roleLabel="Student" homePath="/student" onNavigate={() => setNavOpen(false)} />
      <div className="vmt-drawer-backdrop" onClick={() => setNavOpen(false)} aria-hidden="true" />
      <div className="vmt-app">
        <Navbar variant="app" onMenuClick={() => setNavOpen(true)} profilePath="/student/profile" notificationsPath="/student/notifications" />
        <main className="vmt-main" id="main">
          <div className="vmt-container">
            <Suspense fallback={<LoadingSpinner label="Loading…" />}>
              <Outlet />
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
}

/** Student area: sidebar + top bar (with the notifications bell) around the student pages. */
export default function StudentLayout() {
  return (
    <NotificationProvider>
      <StudentShell />
    </NotificationProvider>
  );
}
