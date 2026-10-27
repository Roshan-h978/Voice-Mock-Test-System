import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { ChartColumn, ClipboardList, LayoutDashboard, MessageSquare, User, Users } from 'lucide-react';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import { getAttempts } from '../services/adminService';

/** Admin area: sidebar (with the review-queue count) + top bar around the admin pages. */
export default function AdminLayout() {
  const [navOpen, setNavOpen] = useState(false);
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
    { to: '/admin/profile', label: 'Profile', icon: User },
  ];

  return (
    <div className={`vmt-shell${navOpen ? ' is-nav-open' : ''}`}>
      <Sidebar items={navItems} roleLabel="Admin" homePath="/admin" onNavigate={() => setNavOpen(false)} />
      <div className="vmt-drawer-backdrop" onClick={() => setNavOpen(false)} aria-hidden="true" />
      <div className="vmt-app">
        <Navbar variant="app" onMenuClick={() => setNavOpen(true)} profilePath="/admin/profile" />
        <main className="vmt-main" id="main">
          <div className="vmt-container">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
