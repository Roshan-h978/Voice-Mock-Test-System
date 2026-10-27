import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Alert from '../../components/Alert';
import AuthShell from '../../components/AuthShell';
import Button from '../../components/Button';
import GoogleSignInButton from '../../components/GoogleSignInButton';
import TextField from '../../components/TextField';
import { useAuth } from '../../context/AuthContext';
import { getErrorMessage } from '../../services/api';
import { homeFor } from '../../utils/constants';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.email.trim() || !form.password) {
      setError('Enter your email and password.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const user = await login(form.email.trim(), form.password);
      navigate(homeFor(user, location.state?.from?.pathname), { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, 'Sign-in failed. Please try again.'));
      setSubmitting(false);
    }
  };

  return (
    <AuthShell title="Welcome back" subtitle="Sign in to continue your speaking practice.">
      {location.state?.notice && <Alert tone="success">{location.state.notice}</Alert>}
      <GoogleSignInButton text="signin_with" />
      {error && <Alert tone="danger">{error}</Alert>}

      <form className="vmt-form" onSubmit={handleSubmit} noValidate>
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          value={form.email}
          onChange={update('email')}
          placeholder="Enter your email"
          required
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          value={form.password}
          onChange={update('password')}
          required
        />
        <div className="vmt-row vmt-row-between">
          <span />
          <Link to="/forgot-password" className="vmt-link body-sm">
            Forgot password?
          </Link>
        </div>
        <Button type="submit" block loading={submitting}>
          Sign in
        </Button>
      </form>

      <p className="body-sm vmt-muted">
        New here?{' '}
        <Link to="/register" className="vmt-link">
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}
