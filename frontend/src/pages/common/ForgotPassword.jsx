import { useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import Alert from '../../components/Alert';
import AuthShell from '../../components/AuthShell';
import Button from '../../components/Button';
import TextField from '../../components/TextField';
import { getErrorMessage } from '../../services/api';
import { requestPasswordReset } from '../../services/authService';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [sentMessage, setSentMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) {
      setError('Enter a valid email address.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const data = await requestPasswordReset(email.trim());
      setSentMessage(data.detail);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell title="Forgot your password?" subtitle="Enter your email and we'll send you a link to choose a new one.">
      {sentMessage ? (
        <Alert tone="success" title="Check your email">
          {sentMessage} If you don't see it in a few minutes, check your spam folder.
        </Alert>
      ) : (
        <form className="vmt-form" onSubmit={handleSubmit} noValidate>
          {error && <Alert tone="danger">{error}</Alert>}
          <TextField
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            required
          />
          <Button type="submit" block loading={submitting}>
            Send reset link
          </Button>
        </form>
      )}
      <Link to="/login" className="vmt-crumb">
        <ArrowLeft className="vmt-icon-sm" aria-hidden="true" />
        Back to sign in
      </Link>
    </AuthShell>
  );
}
