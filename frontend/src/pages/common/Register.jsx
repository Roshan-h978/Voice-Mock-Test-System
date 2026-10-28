import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import Alert from '../../components/Alert';
import AuthShell from '../../components/AuthShell';
import Button from '../../components/Button';
import GoogleSignInButton from '../../components/GoogleSignInButton';
import LoadingSpinner from '../../components/LoadingSpinner';
import TextField from '../../components/TextField';
import { useAuth } from '../../context/AuthContext';
import { getErrorMessage, getFieldErrors } from '../../services/api';
import { getInvitation } from '../../services/authService';
import { homeFor } from '../../utils/constants';

const EMPTY_FORM = { full_name: '', email: '', password: '', confirm: '' };

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const inviteToken = searchParams.get('invite') || '';

  const [form, setForm] = useState(EMPTY_FORM);
  const [invitation, setInvitation] = useState(null);
  const [inviteState, setInviteState] = useState(inviteToken ? 'loading' : 'none'); // none | loading | valid | invalid
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // An invitation link prefills the email address and name.
  useEffect(() => {
    if (!inviteToken) return undefined;
    let active = true;
    getInvitation(inviteToken)
      .then((data) => {
        if (!active) return;
        setInvitation(data);
        setForm((current) => ({ ...current, email: data.email, full_name: current.full_name || data.name || '' }));
        setInviteState('valid');
      })
      .catch(() => active && setInviteState('invalid'));
    return () => {
      active = false;
    };
  }, [inviteToken]);

  const update = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
    setErrors((current) => ({ ...current, [field]: '' }));
  };

  const validate = () => {
    const found = {};
    if (form.full_name.trim().length < 2) found.full_name = 'Enter your full name.';
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) found.email = 'Enter a valid email address.';
    if (form.password.length < 8) found.password = 'Use at least 8 characters.';
    if (form.confirm !== form.password) found.confirm = 'The passwords do not match.';
    setErrors(found);
    return Object.keys(found).length === 0;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError('');
    if (!validate()) return;
    setSubmitting(true);
    try {
      const user = await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
        ...(inviteState === 'valid' ? { invite_token: inviteToken } : {}),
      });
      navigate(homeFor(user), { replace: true });
    } catch (err) {
      const fieldErrors = getFieldErrors(err);
      setErrors(fieldErrors);
      if (!Object.keys(fieldErrors).length || fieldErrors.invite_token) {
        setFormError(fieldErrors.invite_token || getErrorMessage(err, 'We could not create your account.'));
      }
      setSubmitting(false);
    }
  };

  if (inviteState === 'loading') return <LoadingSpinner fullScreen label="Checking your invitation…" />;

  const isAdminInvite = invitation?.role === 'admin';

  return (
    <AuthShell
      title={invitation ? 'Set up your account' : 'Create your account'}
      subtitle={invitation ? 'Choose a password to finish setting up your account.' : 'Start practising English speaking today.'}
    >
      {inviteState === 'valid' && (
        <Alert tone="success" title={isAdminInvite ? "You're invited as an admin" : "You're invited"}>
          Your account will use {invitation.email}.
        </Alert>
      )}
      {inviteState === 'invalid' && (
        <Alert tone="warning" title="This invitation link has expired or was already used">
          Ask for a new invitation, or create an account below.
        </Alert>
      )}
      <GoogleSignInButton text="signup_with" inviteToken={inviteState === 'valid' ? inviteToken : ''} />
      {formError && <Alert tone="danger">{formError}</Alert>}

      <form className="vmt-form" onSubmit={handleSubmit} noValidate>
        <TextField label="Full name" autoComplete="name" value={form.full_name} onChange={update('full_name')} error={errors.full_name} required />
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          value={form.email}
          onChange={update('email')}
          error={errors.email}
          readOnly={inviteState === 'valid'}
          required
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="new-password"
          value={form.password}
          onChange={update('password')}
          error={errors.password}
          help="At least 8 characters. Avoid common words and only numbers."
          required
        />
        <TextField
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          value={form.confirm}
          onChange={update('confirm')}
          error={errors.confirm}
          required
        />
        <Button type="submit" block loading={submitting}>
          {invitation ? 'Set up my account' : 'Create account'}
        </Button>
        <p className="caption vmt-muted">
          By creating an account you agree to the{' '}
          <Link to="/terms" className="vmt-link">
            terms of use
          </Link>{' '}
          and{' '}
          <Link to="/privacy" className="vmt-link">
            privacy notice
          </Link>
          .
        </p>
      </form>

      <p className="body-sm vmt-muted">
        Already have an account?{' '}
        <Link to="/login" className="vmt-link">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
