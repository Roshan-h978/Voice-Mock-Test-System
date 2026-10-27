import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import Alert from '../../components/Alert';
import AuthShell from '../../components/AuthShell';
import Button from '../../components/Button';
import TextField from '../../components/TextField';
import { getErrorMessage, getFieldErrors } from '../../services/api';
import { confirmPasswordReset } from '../../services/authService';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';
  const [form, setForm] = useState({ password: '', confirm: '' });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!token) {
    return (
      <AuthShell title="Reset your password">
        <Alert tone="warning" title="This link is incomplete">
          Open the link from your email again, or ask for a new one.
        </Alert>
        <Button to="/forgot-password" block>
          Send me a new link
        </Button>
      </AuthShell>
    );
  }

  const update = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
    setErrors((current) => ({ ...current, [field]: '' }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const found = {};
    if (form.password.length < 8) found.password = 'Use at least 8 characters.';
    if (form.confirm !== form.password) found.confirm = 'The passwords do not match.';
    setErrors(found);
    if (Object.keys(found).length) return;

    setSubmitting(true);
    setFormError('');
    try {
      const data = await confirmPasswordReset(token, form.password);
      navigate('/login', { replace: true, state: { notice: data.detail } });
    } catch (err) {
      const fieldErrors = getFieldErrors(err);
      if (fieldErrors.new_password) setErrors({ password: fieldErrors.new_password });
      else setFormError(fieldErrors.token || getErrorMessage(err));
      setSubmitting(false);
    }
  };

  return (
    <AuthShell title="Choose a new password" subtitle="After this you can sign in with your new password.">
      {formError && (
        <Alert tone="danger">
          {formError}{' '}
          <Link to="/forgot-password" className="vmt-link">
            Ask for a new link
          </Link>
        </Alert>
      )}
      <form className="vmt-form" onSubmit={handleSubmit} noValidate>
        <TextField
          label="New password"
          type="password"
          autoComplete="new-password"
          value={form.password}
          onChange={update('password')}
          error={errors.password}
          help="At least 8 characters. Avoid common words and only numbers."
          required
        />
        <TextField
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          value={form.confirm}
          onChange={update('confirm')}
          error={errors.confirm}
          required
        />
        <Button type="submit" block loading={submitting}>
          Save new password
        </Button>
      </form>
    </AuthShell>
  );
}
