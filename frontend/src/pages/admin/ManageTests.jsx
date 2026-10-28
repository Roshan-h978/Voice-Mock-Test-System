import { useCallback, useEffect, useRef, useState } from 'react';
import { Archive, ClipboardList, ListChecks, Pencil, Plus, Send, Trash2, Undo2 } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import Alert from '../../components/Alert';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import LoadingSpinner from '../../components/LoadingSpinner';
import Modal from '../../components/Modal';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import TextField from '../../components/TextField';
import { createTest, deleteTest, getTests, updateTest } from '../../services/adminService';
import { getErrorMessage, getFieldErrors } from '../../services/api';
import { LEVELS } from '../../utils/constants';
import { formatScore, levelLabel } from '../../utils/formatters';

const STATUS_TABS = [
  { value: '', label: 'All' },
  { value: 'published', label: 'Published' },
  { value: 'draft', label: 'Drafts' },
  { value: 'archived', label: 'Archived' },
];
const EMPTY_TEST = { title: '', description: '', level: 'beginner', prep_seconds: 15, answer_seconds: 60, allow_retake: true };

export default function ManageTests() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState('');
  const [tests, setTests] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const [form, setForm] = useState(null); // null = closed; { id?, ...fields }
  const [formErrors, setFormErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [busyId, setBusyId] = useState(null);

  // Only the newest request may fill the table (an older, slower answer would show the wrong tab).
  const latestRequest = useRef(0);
  const load = useCallback(async () => {
    const request = latestRequest.current + 1;
    latestRequest.current = request;
    setError('');
    try {
      const data = await getTests(status ? { status } : {});
      if (request === latestRequest.current) setTests(data);
    } catch (err) {
      if (request === latestRequest.current) setError(getErrorMessage(err, 'Tests could not be loaded.'));
    }
  }, [status]);

  useEffect(() => {
    load();
  }, [load]);

  // /admin/tests?new=1 (from the dashboard) opens the "New test" form.
  useEffect(() => {
    if (searchParams.get('new') === '1') {
      setForm({ ...EMPTY_TEST });
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const openCreate = () => {
    setFormErrors({});
    setForm({ ...EMPTY_TEST });
  };

  const openEdit = (test) => {
    setFormErrors({});
    setForm({
      id: test.id,
      title: test.title,
      description: test.description,
      level: test.level,
      prep_seconds: test.prep_seconds,
      answer_seconds: test.answer_seconds,
      allow_retake: test.allow_retake,
    });
  };

  const saveForm = async (event) => {
    event.preventDefault();
    if (form.title.trim().length < 3) {
      setFormErrors({ title: 'Give the test a title of at least 3 characters.' });
      return;
    }
    setSaving(true);
    setFormErrors({});
    const { id, ...fields } = form;
    const payload = { ...fields, prep_seconds: Number(fields.prep_seconds), answer_seconds: Number(fields.answer_seconds) };
    try {
      if (id) {
        await updateTest(id, payload);
        setNotice('Test saved.');
      } else {
        const created = await createTest(payload);
        setNotice(`"${created.title}" was created as a draft. Add questions, then publish it.`);
      }
      setForm(null);
      load();
    } catch (err) {
      const fieldErrors = getFieldErrors(err);
      setFormErrors(Object.keys(fieldErrors).length ? fieldErrors : { form: getErrorMessage(err) });
    } finally {
      setSaving(false);
    }
  };

  const changeStatus = async (test, nextStatus, message) => {
    setBusyId(test.id);
    setError('');
    try {
      await updateTest(test.id, { status: nextStatus });
      setNotice(message);
      load();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const removeTest = async () => {
    const test = confirmDelete;
    setSaving(true);
    try {
      await deleteTest(test.id, { withResults: true }); // the dialog already said the results go too
      setNotice(test.attempt_count ? `"${test.title}" and its results were deleted.` : `"${test.title}" was deleted.`);
      setConfirmDelete(null);
      load();
    } catch (err) {
      setError(getErrorMessage(err));
      setConfirmDelete(null);
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    setForm((current) => ({ ...current, [field]: value }));
  };

  return (
    <>
      <PageHeader
        overline="Content"
        title="Mock tests"
        subtitle="Create tests, add questions and publish them for students."
        actions={
          <Button icon={Plus} onClick={openCreate}>
            New test
          </Button>
        }
      />

      <div className="vmt-tabs" role="tablist" aria-label="Filter tests">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.label}
            type="button"
            role="tab"
            aria-selected={status === tab.value}
            className={`vmt-tab${status === tab.value ? ' is-active' : ''}`}
            onClick={() => setStatus(tab.value)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {notice && (
        <Alert tone="success" onClose={() => setNotice('')}>
          {notice}
        </Alert>
      )}
      {error && (
        <Alert tone="danger" onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {!tests && !error && <LoadingSpinner label="Loading tests…" />}

      {tests && tests.length === 0 && (
        <div className="vmt-card">
          <EmptyState icon={ClipboardList} title="No tests here" action={<Button icon={Plus} onClick={openCreate}>Create a test</Button>}>
            {status ? 'Nothing matches this filter.' : 'Create your first mock test.'}
          </EmptyState>
        </div>
      )}

      {tests && tests.length > 0 && (
        <div className="vmt-table-wrap">
          <table className="vmt-table" style={{ minWidth: 900 }}>
            <thead>
              <tr>
                <th scope="col">Test</th>
                <th scope="col">Level</th>
                <th scope="col" className="is-num">Questions</th>
                <th scope="col" className="is-num">Taken</th>
                <th scope="col" className="is-num">Average</th>
                <th scope="col">Status</th>
                <th scope="col" className="is-actions">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {tests.map((test) => (
                <tr key={test.id}>
                  <td style={{ maxWidth: 320 }}>
                    <span className="vmt-cell-main">{test.title}</span>
                    {test.description && (
                      <>
                        <br />
                        <span className="caption vmt-muted">{test.description.slice(0, 90)}</span>
                      </>
                    )}
                  </td>
                  <td>{levelLabel(test.level)}</td>
                  <td className="is-num">{test.question_count}</td>
                  <td className="is-num">{test.attempt_count}</td>
                  <td className="is-num">{formatScore(test.average_score)}</td>
                  <td>
                    <StatusBadge kind="test" status={test.status} />
                  </td>
                  <td className="is-actions">
                    <div className="vmt-row vmt-row-tight" style={{ justifyContent: 'flex-end', flexWrap: 'nowrap' }}>
                      <Button size="sm" variant="secondary" icon={ListChecks} to={`/admin/tests/${test.id}/questions`}>
                        Questions
                      </Button>
                      <Button size="sm" variant="ghost" icon={Pencil} onClick={() => openEdit(test)} aria-label={`Edit ${test.title}`}>
                        Edit
                      </Button>
                      {test.status === 'draft' && (
                        <Button
                          size="sm"
                          icon={Send}
                          loading={busyId === test.id}
                          onClick={() => changeStatus(test, 'published', `"${test.title}" is now visible to students.`)}
                        >
                          Publish
                        </Button>
                      )}
                      {test.status === 'published' && (
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={Archive}
                          loading={busyId === test.id}
                          onClick={() => changeStatus(test, 'archived', `"${test.title}" is archived and hidden from students.`)}
                        >
                          Archive
                        </Button>
                      )}
                      {test.status === 'archived' && (
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={Undo2}
                          loading={busyId === test.id}
                          onClick={() => changeStatus(test, 'draft', `"${test.title}" is back in drafts.`)}
                        >
                          Restore
                        </Button>
                      )}
                      <button
                        type="button"
                        className="vmt-icon-btn vmt-icon-btn-sm"
                        onClick={() => setConfirmDelete(test)}
                        aria-label={`Delete ${test.title}`}
                        title="Delete"
                      >
                        <Trash2 className="vmt-icon" aria-hidden="true" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={Boolean(form)}
        title={form?.id ? 'Edit test' : 'New test'}
        description={form?.id ? undefined : 'New tests start as drafts. Students see them after you publish.'}
        onClose={() => setForm(null)}
        wide
      >
        {form && (
          <form className="vmt-form" onSubmit={saveForm} noValidate>
            {formErrors.form && <Alert tone="danger">{formErrors.form}</Alert>}
            {formErrors.status && <Alert tone="danger">{formErrors.status}</Alert>}
            <TextField label="Title" value={form.title} onChange={updateField('title')} error={formErrors.title} placeholder="Everyday conversation" />
            <TextField
              as="textarea"
              label="Description (optional)"
              value={form.description}
              onChange={updateField('description')}
              error={formErrors.description}
              rows={3}
              placeholder="What the test covers and who it is for."
            />
            <div className="vmt-form-grid">
              <TextField as="select" label="Level" value={form.level} onChange={updateField('level')}>
                {LEVELS.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </TextField>
              <div />
              <TextField
                label="Thinking time (seconds)"
                type="number"
                min={0}
                max={300}
                value={form.prep_seconds}
                onChange={updateField('prep_seconds')}
                error={formErrors.prep_seconds}
              />
              <TextField
                label="Speaking time (seconds)"
                type="number"
                min={10}
                max={300}
                value={form.answer_seconds}
                onChange={updateField('answer_seconds')}
                error={formErrors.answer_seconds}
              />
            </div>
            <label className="vmt-check">
              <input type="checkbox" checked={form.allow_retake} onChange={updateField('allow_retake')} />
              Students can take this test more than once
            </label>
            <div className="vmt-modal-actions">
              <Button variant="secondary" onClick={() => setForm(null)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {form.id ? 'Save changes' : 'Create test'}
              </Button>
            </div>
          </form>
        )}
      </Modal>

      <Modal
        open={Boolean(confirmDelete)}
        title={`Delete "${confirmDelete?.title}"?`}
        description={
          confirmDelete?.attempt_count
            ? `Students have taken this test. The test, its questions and ${confirmDelete.attempt_count} ${confirmDelete.attempt_count === 1 ? 'result' : 'results'} with their recordings are removed for good. To keep the results, archive the test instead.`
            : 'The test and its questions are removed for good.'
        }
        onClose={() => setConfirmDelete(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
            <Button variant="danger" loading={saving} onClick={removeTest}>
              {confirmDelete?.attempt_count ? 'Delete test and results' : 'Delete test'}
            </Button>
          </>
        }
      />
    </>
  );
}
