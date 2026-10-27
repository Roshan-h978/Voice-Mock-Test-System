import { Link } from 'react-router-dom';
import { APP_NAME } from '../utils/constants';
import Brand from './Brand';

export default function Footer() {
  return (
    <footer className="vmt-footer">
      <div className="vmt-footer-inner">
        <Brand />
        <nav className="vmt-footer-links" aria-label="Footer">
          <Link to="/login">Sign in</Link>
          <Link to="/register">Create account</Link>
          <Link to="/forgot-password">Forgot password</Link>
        </nav>
        <span>
          © {new Date().getFullYear()} {APP_NAME}. English speaking practice.
        </span>
      </div>
    </footer>
  );
}
