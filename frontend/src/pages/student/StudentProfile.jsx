import { useEffect, useState } from 'react';
import { KeyRound, UserRound } from 'lucide-react';
import Alert from '../../components/Alert';
import Button from '../../components/Button';
import PageHeader from '../../components/PageHeader';
import TextField from '../../components/TextField';
import { useAuth } from '../../context/AuthContext';
import { getErrorMessage, getFieldErrors } from '../../services/api';
import { changePassword, updateMe } from '../../services/authService';
import { LEVELS } from '../../utils/constants';
import { formatDate } from '../../utils/formatters';

const EMPTY_PASSWORDS = { current: '', next: '', confirm: '' };

/** Profile and password page. Used by students and (without the level field) by admins. */
export default function StudentProfile() {
  const { user, setUser, refreshUser } = useAuth();
  const isStudent = user?.role === 'student';

  const [profile, setProfile] = useState({ full_name: '', phone: '', level: 'beginner' });
  const [profileErrors, setProfileErrors] = useState({});
  const [profileMessage, setProfileMessage] = useState(null);
  const [savingProfile, setSavingProfile] = useState(false);

  const [passwords, setPasswords] = useState(EMPTY_PASSWORDS);
  const [passwordErrors, setPasswordErrors] = useState({});
  const [passwordMessage, setPasswordMessage] = useState(null);
  const [savingPassword, setSavingPassword] = useState(false);

  // Fill the form from the saved profile. Only the saved values are watched, so refreshing the
  // account after a password change doesn't wipe details that are being typed.
  const savedName = user?.full_name ?? '';
  const savedPhone = user?.phone || '';
  const savedLevel = user?.level || 'beginner';
  useEffect(() => {
    setProfile({ full_name: savedName, phone: savedPhone, level: savedLevel });
  }, [savedName, savedPhone, savedLevel]);

  const saveProfile = async (event) => {
    event.preventDefault();
    if (profile.full_name.trim().length < 2) {
      setProfileErrors({ full_name: 'Enter your full name.' });
      return;
    }
    setSavingProfile(true);
    setProfileErrors({});
    setProfileMessage(null);
    try {
      const payload = { full_name: profile.full_name.trim(), phone: profile.phone.trim() };
      if (isStudent) payload.level = profile.level;
      const updated = await updateMe(payload);
      setUser(updated);
      setProfileMessage({ tone: 'success', text: 'Your profile has been saved.' });
    } catch (err) {
      setProfileErrors(getFieldErrors(err));
      setProfileMessage({ tone: 'danger', text: getErrorMessage(err, 'Your profile could not be saved.') });
    } finally {
      setSavingProfile(false);
    }
  };

  const savePassword = async (event) => {
    event.preventDefault();
    const found = {};
    if (!passwords.current) found.current_password = 'Enter your current password.';
    if (passwords.next.length < 8) found.new_password = 'Use at least 8 characters.';
    if (passwords.confirm !== passwords.next) found.confirm = 'The passwords do not match.';
    setPasswordErrors(found);
    setPasswordMessage(null);
    if (Object.keys(found).length) return;

    setSavingPassword(true);
    try {
      const data = await changePassword(passwords.current, passwords.next);
      setPasswords(EMPTY_PASSWORDS);
      setPasswordMessage({ tone: 'success', text: data.detail });
      refreshUser().catch(() => {});
    } catch (err) {
      setPasswordErrors(getFieldErrors(err));
      setPasswordMessage({ tone: 'danger', text: getErrorMessage(err, 'Your password could not be changed.') });
    } finally {
      setSavingPassword(false);
    }
  };

  const updateProfile = (field) => (event) => setProfile((current) => ({ ...current, [field]: event.target.value }));
  const updatePassword = (field) => (event) => setPasswords((current) => ({ ...current, [field]: event.target.value }));

  return (
    <>
      <PageHeader
        overline="Account"
        title="My profile"
        subtitle={user ? `${user.role === 'admin' ? 'Admin' : 'Student'} account · joined ${formatDate(user.date_joined)}` : ''}
      />

      <div className="vmt-grid-wide">
        <form className="vmt-card vmt-form" onSubmit={saveProfile} noValidate>
          <div className="vmt-row vmt-row-tight">
            <UserRound className="vmt-icon vmt-teal" aria-hidden="true" />
            <h2 className="title-sm">Personal details</h2>
          </div>
          {profileMessage && <Alert tone={profileMessage.tone}>{profileMessage.text}</Alert>}
          <TextField label="Full name" value={profile.full_name} onChange={updateProfile('full_name')} error={profileErrors.full_name} autoComplete="name" />
          <TextField label="Email" value={user?.email || ''} readOnly help="Contact an admin to change your email address." />
          <TextField label="Phone (optional)" type="tel" value={profile.phone} onChange={updateProfile('phone')} error={profileErrors.phone} autoComplete="tel" />
          {isStudent && (
            <TextField
              as="select"
              label="English level"
              value={profile.level}
              onChange={updateProfile('level')}
              help="Helps us give feedback at the right level."
            >
              {LEVELS.map((level) => (
                <option key={level.value} value={level.value}>
                  {level.label}
                </option>
              ))}
            </TextField>
          )}
          <div>
            <Button type="submit" loading={savingProfile}>
              Save changes
            </Button>
          </div>
        </form>

        <form className="vmt-card vmt-form" onSubmit={savePassword} noValidate>
          <div className="vmt-row vmt-row-tight">
            <KeyRound className="vmt-icon vmt-teal" aria-hidden="true" />
            <h2 className="title-sm">Change password</h2>
          </div>
          {user?.uses_default_password && !passwordMessage && (
            <Alert tone="warning">You're using the starting password. Choose your own password here.</Alert>
          )}
          {passwordMessage && <Alert tone={passwordMessage.tone}>{passwordMessage.text}</Alert>}
          <TextField
            label="Current password"
            type="password"
            autoComplete="current-password"
            value={passwords.current}
            onChange={updatePassword('current')}
            error={passwordErrors.current_password}
          />
          <TextField
            label="New password"
            type="password"
            autoComplete="new-password"
            value={passwords.next}
            onChange={updatePassword('next')}
            error={passwordErrors.new_password}
            help="At least 8 characters."
          />
          <TextField
            label="Confirm new password"
            type="password"
            autoComplete="new-password"
            value={passwords.confirm}
            onChange={updatePassword('confirm')}
            error={passwordErrors.confirm}
          />
          <div>
            <Button type="submit" variant="secondary" loading={savingPassword}>
              Change password
            </Button>
          </div>
        </form>
      </div>
    </>
  );
}
