import { useCallback, useEffect, useRef, useState } from 'react';
import { Copy, Pencil, Search, UserPlus, Users } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import Alert from '../../components/Alert';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import LoadingSpinner from '../../components/LoadingSpinner';
import Modal from '../../components/Modal';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import TextField from '../../components/TextField';
import { useAuth } from '../../context/AuthContext';
import { getUsers, inviteUser, updateUser } from '../../services/adminService';
import { getErrorMessage, getFieldErrors } from '../../services/api';
import { LEVELS, PAGE_SIZE } from '../../utils/constants';
import { formatDate, formatScore, initials, levelLabel } from '../../utils/formatters';

const ROLE_TABS = [
  { value: 'student', label: 'Students' },
  { value: 'admin', label: 'Admins' },
];
const EMPTY_INVITE = { email: '', full_name: '', role: 'student' };

export default function ManageStudents() {
  const { user: currentUser, refreshUser } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const [role, setRole] = useState('student');
  const [searchText, setSearchText] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [level, setLevel] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const [inviteOpen, setInviteOpen] = useState(searchParams.get('invite') === '1');
  const [inviteForm, setInviteForm] = useState(EMPTY_INVITE);
  const [inviteErrors, setInviteErrors] = useState({});
  const [inviteResult, setInviteResult] = useState(null);
  const [inviting, setInviting] = useState(false);

  const [editing, setEditing] = useState(null);
  const [editErrors, setEditErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [confirmUser, setConfirmUser] = useState(null);

  // Wait until typing pauses before searching.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchText.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchText]);

  // Only the newest request may fill the table (an older, slower answer would show the wrong list).
  const latestRequest = useRef(0);
  const load = useCallback(async () => {
    const request = latestRequest.current + 1;
    latestRequest.current = request;
    setError('');
    try {
      const response = await getUsers({
        role,
        search: search || undefined,
        status: status || undefined,
        // The level filter is only shown on the Students tab, so it must not hide admins.
        level: role === 'student' && level ? level : undefined,
        page,
        page_size: PAGE_SIZE,
      });
      if (request === latestRequest.current) setData(response);
    } catch (err) {
      if (request === latestRequest.current) setError(getErrorMessage(err, 'The list could not be loaded.'));
    }
  }, [role, search, status, level, page]);

  useEffect(() => {
    load();
  }, [load]);

  // ---- Invite --------------------------------------------------------------
  const openInvite = () => {
    setInviteForm({ ...EMPTY_INVITE, role });
    setInviteErrors({});
    setInviteResult(null);
    setInviteOpen(true);
  };

  const closeInvite = () => {
    setInviteOpen(false);
    if (searchParams.get('invite')) setSearchParams({}, { replace: true });
  };

  const sendInvite = async (event) => {
    event.preventDefault();
    if (!/^\S+@\S+\.\S+$/.test(inviteForm.email.trim())) {
      setInviteErrors({ email: 'Enter a valid email address.' });
      return;
    }
    setInviting(true);
    setInviteErrors({});
    try {
      const result = await inviteUser({ ...inviteForm, email: inviteForm.email.trim(), full_name: inviteForm.full_name.trim() });
      setInviteResult(result);
    } catch (err) {
      const fieldErrors = getFieldErrors(err);
      setInviteErrors(Object.keys(fieldErrors).length ? fieldErrors : { form: getErrorMessage(err) });
    } finally {
      setInviting(false);
    }
  };

  // ---- Edit and suspend -----------------------------------------------------
  const saveEdit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setEditErrors({});
    try {
      await updateUser(editing.id, { full_name: editing.full_name, level: editing.level, role: editing.role });
      if (editing.id === currentUser?.id) refreshUser().catch(() => {}); // the name in the sidebar and top bar
      setEditing(null);
      setNotice('Changes saved.');
      load();
    } catch (err) {
      const fieldErrors = getFieldErrors(err);
      setEditErrors(Object.keys(fieldErrors).length ? fieldErrors : { form: getErrorMessage(err) });
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async () => {
    const target = confirmUser;
    setSaving(true);
    try {
      await updateUser(target.id, { is_active: !target.is_active });
      setNotice(target.is_active ? `${target.full_name} is suspended.` : `${target.full_name} can sign in again.`);
      setConfirmUser(null);
      load();
    } catch (err) {
      setError(getErrorMessage(err));
      setConfirmUser(null);
    } finally {
      setSaving(false);
    }
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;

  return (
    <>
      <PageHeader
        overline="People"
        title="Students and admins"
        subtitle="Invite people, update their level and suspend accounts."
        actions={
          <Button icon={UserPlus} onClick={openInvite}>
            Invite
          </Button>
        }
      />

      <div className="vmt-tabs" role="tablist" aria-label="Role">
        {ROLE_TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={role === tab.value}
            className={`vmt-tab${role === tab.value ? ' is-active' : ''}`}
            onClick={() => {
              setRole(tab.value);
              setPage(1);
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="vmt-toolbar">
        <div className="vmt-field vmt-search">
          <label className="vmt-label" htmlFor="people-search">
            Search
          </label>
          <div className="vmt-input-wrap has-icon">
            <Search className="vmt-icon vmt-input-icon" aria-hidden="true" />
            <input
              id="people-search"
              className="vmt-input"
              type="search"
              placeholder="Name or email"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
            />
          </div>
        </div>
        <TextField as="select" label="Status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}>
          <option value="">All</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
        </TextField>
        {role === 'student' && (
          <TextField as="select" label="Level" value={level} onChange={(event) => { setLevel(event.target.value); setPage(1); }}>
            <option value="">All levels</option>
            {LEVELS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </TextField>
        )}
      </div>

      {notice && (
        <Alert tone="success" onClose={() => setNotice('')}>
          {notice}
        </Alert>
      )}
      {error && <Alert tone="danger">{error}</Alert>}
      {!data && !error && <LoadingSpinner label="Loading…" />}

      {data && data.results.length === 0 && (
        <div className="vmt-card">
          <EmptyState icon={Users} title="No one found" action={<Button onClick={openInvite} icon={UserPlus}>Invite someone</Button>}>
            {search || status || (role === 'student' && level) ? 'Try a different search or filter.' : 'Invite your first student to get started.'}
          </EmptyState>
        </div>
      )}

      {data && data.results.length > 0 && (
        <>
          <div className="vmt-table-wrap">
            <table className="vmt-table">
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  {role === 'student' && <th scope="col">Level</th>}
                  {role === 'student' && <th scope="col" className="is-num">Tests</th>}
                  {role === 'student' && <th scope="col" className="is-num">Average</th>}
                  <th scope="col">{role === 'student' ? 'Last test' : 'Joined'}</th>
                  <th scope="col">Status</th>
                  <th scope="col" className="is-actions">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((person) => {
                  const isSelf = person.id === currentUser?.id;
                  return (
                    <tr key={person.id}>
                      <td>
                        <div className="vmt-person">
                          <span className="vmt-avatar vmt-avatar-sm" aria-hidden="true">
                            {initials(person.full_name)}
                          </span>
                          <span className="vmt-person-text">
                            <span className="vmt-cell-main">
                              {person.full_name}
                              {isSelf ? ' (you)' : ''}
                            </span>
                            <span className="caption vmt-muted">{person.email}</span>
                          </span>
                        </div>
                      </td>
                      {role === 'student' && <td>{levelLabel(person.level)}</td>}
                      {role === 'student' && <td className="is-num">{person.attempt_count ?? 0}</td>}
                      {role === 'student' && <td className="is-num">{formatScore(person.average_score)}</td>}
                      <td>{formatDate(role === 'student' ? person.last_attempt_at : person.date_joined)}</td>
                      <td>
                        <StatusBadge kind="user" status={person.is_active ? 'active' : 'suspended'} />
                      </td>
                      <td className="is-actions">
                        <div className="vmt-row vmt-row-tight" style={{ justifyContent: 'flex-end', flexWrap: 'nowrap' }}>
                          <Button size="sm" variant="ghost" icon={Pencil} onClick={() => { setEditErrors({}); setEditing({ ...person }); }}>
                            Edit
                          </Button>
                          {!isSelf && (
                            <Button size="sm" variant={person.is_active ? 'secondary' : 'primary'} onClick={() => setConfirmUser(person)}>
                              {person.is_active ? 'Suspend' : 'Activate'}
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="vmt-pagination">
            <span className="body-sm vmt-muted">
              {data.count} {data.count === 1 ? 'person' : 'people'} · page {page} of {totalPages}
            </span>
            {totalPages > 1 && (
              <div className="vmt-row vmt-row-tight">
                <Button size="sm" variant="secondary" disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <Button size="sm" variant="secondary" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            )}
          </div>
        </>
      )}

      {/* Invite */}
      <Modal open={inviteOpen} title="Invite someone" description="They get an email with a link to set up their account." onClose={closeInvite}>
        {inviteResult ? (
          <div className="vmt-stack">
            {inviteResult.email_sent ? (
              <Alert tone="success" title="Invitation sent">
                {inviteResult.email} can set up their account with the link in the email. It works until{' '}
                {formatDate(inviteResult.expires_at)}.
              </Alert>
            ) : (
              <>
                <Alert tone="warning" title="The email could not be sent">
                  Share this link with {inviteResult.email} yourself. It works until {formatDate(inviteResult.expires_at)}.
                </Alert>
                <div className="vmt-transcript" style={{ wordBreak: 'break-all' }}>
                  {inviteResult.invite_link}
                </div>
                <div>
                  <Button size="sm" variant="secondary" icon={Copy} onClick={() => navigator.clipboard?.writeText(inviteResult.invite_link)}>
                    Copy link
                  </Button>
                </div>
              </>
            )}
            <div className="vmt-modal-actions">
              <Button variant="secondary" onClick={() => { setInviteResult(null); setInviteForm({ ...EMPTY_INVITE, role }); }}>
                Invite another
              </Button>
              <Button onClick={() => { closeInvite(); load(); }}>Done</Button>
            </div>
          </div>
        ) : (
          <form className="vmt-form" onSubmit={sendInvite} noValidate>
            {inviteErrors.form && <Alert tone="danger">{inviteErrors.form}</Alert>}
            <TextField
              label="Email"
              type="email"
              value={inviteForm.email}
              onChange={(event) => setInviteForm((form) => ({ ...form, email: event.target.value }))}
              error={inviteErrors.email}
              required
            />
            <TextField
              label="Full name (optional)"
              value={inviteForm.full_name}
              onChange={(event) => setInviteForm((form) => ({ ...form, full_name: event.target.value }))}
              error={inviteErrors.full_name}
            />
            <TextField
              as="select"
              label="Role"
              value={inviteForm.role}
              onChange={(event) => setInviteForm((form) => ({ ...form, role: event.target.value }))}
              help="Admins can manage tests, students and reviews."
            >
              <option value="student">Student</option>
              <option value="admin">Admin</option>
            </TextField>
            <div className="vmt-modal-actions">
              <Button variant="secondary" onClick={closeInvite}>
                Cancel
              </Button>
              <Button type="submit" loading={inviting} icon={UserPlus}>
                Send invitation
              </Button>
            </div>
          </form>
        )}
      </Modal>

      {/* Edit */}
      <Modal open={Boolean(editing)} title="Edit account" description={editing?.email} onClose={() => setEditing(null)}>
        {editing && (
          <form className="vmt-form" onSubmit={saveEdit} noValidate>
            {editErrors.form && <Alert tone="danger">{editErrors.form}</Alert>}
            <TextField
              label="Full name"
              value={editing.full_name}
              onChange={(event) => setEditing((item) => ({ ...item, full_name: event.target.value }))}
              error={editErrors.full_name}
            />
            <TextField
              as="select"
              label="English level"
              value={editing.level}
              onChange={(event) => setEditing((item) => ({ ...item, level: event.target.value }))}
            >
              {LEVELS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </TextField>
            <TextField
              as="select"
              label="Role"
              value={editing.role}
              onChange={(event) => setEditing((item) => ({ ...item, role: event.target.value }))}
              disabled={editing.id === currentUser?.id}
              error={editErrors.role}
              help={editing.id === currentUser?.id ? "You can't change your own role." : undefined}
            >
              <option value="student">Student</option>
              <option value="admin">Admin</option>
            </TextField>
            <div className="vmt-modal-actions">
              <Button variant="secondary" onClick={() => setEditing(null)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                Save changes
              </Button>
            </div>
          </form>
        )}
      </Modal>

      {/* Suspend / activate */}
      <Modal
        open={Boolean(confirmUser)}
        title={confirmUser?.is_active ? `Suspend ${confirmUser?.full_name}?` : `Activate ${confirmUser?.full_name}?`}
        description={
          confirmUser?.is_active
            ? "They won't be able to sign in until you activate the account again. Their results are kept."
            : 'They will be able to sign in again.'
        }
        onClose={() => setConfirmUser(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmUser(null)}>
              Cancel
            </Button>
            <Button variant={confirmUser?.is_active ? 'danger' : 'primary'} loading={saving} onClick={toggleActive}>
              {confirmUser?.is_active ? 'Suspend' : 'Activate'}
            </Button>
          </>
        }
      />
    </>
  );
}
