import { useEffect } from 'react';
import { Route, Routes, useLocation } from 'react-router-dom';
import Button from './components/Button';
import EmptyState from './components/EmptyState';
import ProtectedRoute, { GuestRoute } from './components/ProtectedRoute';
import AdminLayout from './layouts/AdminLayout';
import StudentLayout from './layouts/StudentLayout';
import AdminDashboard from './pages/admin/AdminDashboard';
import ManageQuestions from './pages/admin/ManageQuestions';
import ManageStudents from './pages/admin/ManageStudents';
import ManageTests from './pages/admin/ManageTests';
import Reports from './pages/admin/Reports';
import ReviewAttempts from './pages/admin/ReviewAttempts';
import ForgotPassword from './pages/common/ForgotPassword';
import Home from './pages/common/Home';
import Login from './pages/common/Login';
import Privacy from './pages/common/Privacy';
import Register from './pages/common/Register';
import ResetPassword from './pages/common/ResetPassword';
import Terms from './pages/common/Terms';
import AttemptHistory from './pages/student/AttemptHistory';
import SpeakingTest from './pages/student/SpeakingTest';
import StudentDashboard from './pages/student/StudentDashboard';
import StudentProfile from './pages/student/StudentProfile';
import TestInstructions from './pages/student/TestInstructions';
import TestResult from './pages/student/TestResult';

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

function NotFound() {
  return (
    <main className="vmt-focus-main" style={{ minHeight: '100vh', justifyContent: 'center' }}>
      <div className="vmt-card">
        <EmptyState title="Page not found" action={<Button to="/">Go to the home page</Button>}>
          The page you were looking for doesn't exist or has moved.
        </EmptyState>
      </div>
    </main>
  );
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        {/* Public */}
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<GuestRoute><Login /></GuestRoute>} />
        <Route path="/register" element={<GuestRoute><Register /></GuestRoute>} />
        <Route path="/forgot-password" element={<GuestRoute><ForgotPassword /></GuestRoute>} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />

        {/* Student: the speaking test is a focused page without the sidebar */}
        <Route path="/student/attempts/:attemptId" element={<ProtectedRoute role="student"><SpeakingTest /></ProtectedRoute>} />
        <Route path="/student" element={<ProtectedRoute role="student"><StudentLayout /></ProtectedRoute>}>
          <Route index element={<StudentDashboard />} />
          <Route path="tests/:testId" element={<TestInstructions />} />
          <Route path="results/:attemptId" element={<TestResult />} />
          <Route path="history" element={<AttemptHistory />} />
          <Route path="profile" element={<StudentProfile />} />
        </Route>

        {/* Admin */}
        <Route path="/admin" element={<ProtectedRoute role="admin"><AdminLayout /></ProtectedRoute>}>
          <Route index element={<AdminDashboard />} />
          <Route path="students" element={<ManageStudents />} />
          <Route path="tests" element={<ManageTests />} />
          <Route path="tests/:testId/questions" element={<ManageQuestions />} />
          <Route path="reviews" element={<ReviewAttempts />} />
          <Route path="reviews/:attemptId" element={<ReviewAttempts />} />
          <Route path="reports" element={<Reports />} />
          <Route path="profile" element={<StudentProfile />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  );
}
