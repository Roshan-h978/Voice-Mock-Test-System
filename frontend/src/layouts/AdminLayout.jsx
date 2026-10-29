import { Suspense, useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Bell, ChartColumn, ClipboardList, LayoutDashboard, MessageSquare, User, Users } from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import { NotificationProvider, useNotifications } from '../context/NotificationContext';
import { getAttempts } from '../services/adminService';

function AdminShell() {
  const [navOpen, setNavOpen] = useState(false);
  const { unread } = useNotifications();
  const [reviewCount, setReviewCount] = useState(0);
  const location = useLocation();

  // Refresh the "waiting for review" count when the admin moves between pages.
  useEffect(() => {
    let active = true;
    getAttempts({ status: 'needs_review', page_size: 1 })
      .then((data) => active && setReviewCount(data.count || 0))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [location.pathname]);

  const navItems = [
    { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/admin/students', label: 'Students', icon: Users },
    { to: '/admin/tests', label: 'Mock tests', icon: ClipboardList },
    { to: '/admin/reviews', label: 'Reviews', icon: MessageSquare, count: reviewCount },
    { to: '/admin/reports', label: 'Reports', icon: ChartColumn },
    { to: '/admin/notifications', label: 'Notifications', icon: Bell, count: unread, countLabel: 'unread' },
    { to: '/admin/profile', label: 'Profile', icon: User },
  ];

  return (
    <div className={`vmt-shell${navOpen ? ' is-nav-open' : ''}`}>
      <Sidebar items={navItems} roleLabel="Admin" homePath="/admin" onNavigate={() => setNavOpen(false)} />
      <div className="vmt-drawer-backdrop" onClick={() => setNavOpen(false)} aria-hidden="true" />
      <div className="vmt-app">
        <Navbar variant="app" onMenuClick={() => setNavOpen(true)} profilePath="/admin/profile" notificationsPath="/admin/notifications" />
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

/** Admin area: sidebar (with the review-queue count) + top bar (with the notifications bell) around the admin pages. */
export default function AdminLayout() {
  return (
    <NotificationProvider>
      <AdminShell />
    </NotificationProvider>
  );
}
