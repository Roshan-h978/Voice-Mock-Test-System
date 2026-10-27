import { useCallback, useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, ListChecks, Pencil, Plus, Send, Trash2 } from 'lucide-react';
import { useParams } from 'react-router-dom';
import Alert from '../../components/Alert';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import LoadingSpinner from '../../components/LoadingSpinner';
import Modal from '../../components/Modal';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import TextField from '../../components/TextField';
import {
  createQuestion,
  deleteQuestion,
  getQuestions,
  getTest,
  reorderQuestions,
  updateQuestion,
  updateTest,
} from '../../services/adminService';
import { getErrorMessage, getFieldErrors } from '../../services/api';
import { formatDuration, levelLabel, pluralize } from '../../utils/formatters';

const EMPTY_QUESTION = { text: '', hint: '', answer_seconds: '' };

function QuestionForm({ initial, onSave, onCancel, saving, errors, submitLabel }) {
  const [values, setValues] = useState(initial);
  const update = (field) => (event) => setValues((current) => ({ ...current, [field]: event.target.value }));

  return (
    <form
      className="vmt-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(values, () => setValues(EMPTY_QUESTION));
      }}
      noValidate
    >
      {errors.form && <Alert tone="danger">{errors.form}</Alert>}
      <TextField
        as="textarea"
        label="Question"
        rows={3}
        value={values.text}
        onChange={update('text')}
        error={errors.text}
        placeholder="Describe a place you like to visit and explain why."
      />
      <div className="vmt-form-grid">
        <TextField label="Hint (optional)" value={values.hint} onChange={update('hint')} error={errors.hint} placeholder="Where is it? What do you do there?" />
        <TextField
          label="Speaking time (seconds)"
          type="number"
          min={10}
          max={300}
          value={values.answer_seconds}
          onChange={update('answer_seconds')}
          error={errors.answer_seconds}
          help="Leave empty to use the test's time."
        />
      </div>
      <div className="vmt-row vmt-row-tight">
        <Button type="submit" loading={saving} icon={submitLabel === 'Add question' ? Plus : undefined}>
          {submitLabel}
        </Button>
        {onCancel && (
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}

export default function ManageQuestions() {
  const { testId } = useParams();
  const [test, setTest] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [formErrors, setFormErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const load = useCallback(async () => {
    try {
      const [testData, questionData] = await Promise.all([getTest(testId), getQuestions(testId)]);
      setTest(testData);
      setQuestions(questionData);
    } catch (err) {
      setError(getErrorMessage(err, 'This test could not be loaded.'));
    }
  }, [testId]);

  useEffect(() => {
    load();
  }, [load]);

  const payloadFrom = (values) => ({
    text: values.text.trim(),
    hint: values.hint.trim(),
    answer_seconds: values.answer_seconds === '' ? null : Number(values.answer_seconds),
  });

  const handleAdd = async (values, resetForm) => {
    if (values.text.trim().length < 5) {
      setFormErrors({ text: 'Write the question in at least 5 characters.' });
      return;
    }
    setSaving(true);
    setFormErrors({});
    try {
      await createQuestion({ test: Number(testId), ...payloadFrom(values) });
      resetForm();
      setNotice('Question added.');
      load();
    } catch (err) {
      const fieldErrors = getFieldErrors(err);
      setFormErrors(Object.keys(fieldErrors).length ? fieldErrors : { form: getErrorMessage(err) });
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = async (values) => {
    if (values.text.trim().length < 5) {
      setFormErrors({ text: 'Write the question in at least 5 characters.' });
      return;
    }
    setSaving(true);
    setFormErrors({});
    try {
      await updateQuestion(editingId, payloadFrom(values));
      setEditingId(null);
      setNotice('Question saved.');
      load();
    } catch (err) {
      const fieldErrors = getFieldErrors(err);
      setFormErrors(Object.keys(fieldErrors).length ? fieldErrors : { form: getErrorMessage(err) });
    } finally {
      setSaving(false);
    }
  };

  const move = async (position, direction) => {
    const target = position + direction;
    if (target < 0 || target >= questions.length) return;
    const reordered = [...questions];
    [reordered[position], reordered[target]] = [reordered[target], reordered[position]];
    setQuestions(reordered);
    try {
      setQuestions(await reorderQuestions(Number(testId), reordered.map((item) => item.id)));
    } catch (err) {
      setError(getErrorMessage(err));
      load();
    }
  };

  const handleDelete = async () => {
    setSaving(true);
    try {
      await deleteQuestion(confirmDelete.id);
      setNotice('Question deleted.');
      setConfirmDelete(null);
      load();
    } catch (err) {
      setError(getErrorMessage(err));
      setConfirmDelete(null);
    } finally {
      setSaving(false);
    }
  };

  const setStatus = async (status, message) => {
    setError('');
    try {
      setTest(await updateTest(testId, { status }));
      setNotice(message);
    } catch (err) {
      const fieldErrors = getFieldErrors(err);
      setError(fieldErrors.status || getErrorMessage(err));
    }
  };

  if (!test && error) {
    return (
      <>
        <PageHeader title="Test not found" back={{ to: '/admin/tests', label: 'Mock tests' }} />
        <Alert tone="danger">{error}</Alert>
      </>
    );
  }
  if (!test) return <LoadingSpinner label="Loading questions…" />;

  const archived = test.status === 'archived';

  return (
    <>
      <PageHeader
        back={{ to: '/admin/tests', label: 'Mock tests' }}
        overline="Questions"
        title={test.title}
        subtitle={`${levelLabel(test.level)} · ${pluralize(questions.length, 'question')} · ${formatDuration(test.prep_seconds)} thinking, ${formatDuration(test.answer_seconds)} speaking`}
        actions={
          <>
            <StatusBadge kind="test" status={test.status} />
            {test.status === 'draft' && (
              <Button icon={Send} disabled={questions.length === 0} onClick={() => setStatus('published', 'The test is published. Students can take it now.')}>
                Publish test
              </Button>
            )}
            {test.status === 'published' && (
              <Button variant="secondary" onClick={() => setStatus('draft', 'The test is back in drafts and hidden from students.')}>
                Move to draft
              </Button>
            )}
          </>
        }
      />

      {archived && (
        <Alert tone="warning" title="This test is archived">
          Restore it to drafts from the Mock tests page before editing its questions.
        </Alert>
      )}
      {test.status === 'published' && test.attempt_count > 0 && (
        <Alert tone="info">
          Students have taken this test. Saved results keep the question text they answered, so editing is safe.
        </Alert>
      )}
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

      <section className="vmt-stack" aria-label="Questions">
        {questions.length === 0 ? (
          <div className="vmt-card">
            <EmptyState icon={ListChecks} title="No questions yet">
              Add the first question below. Most tests have 3 to 6 questions.
            </EmptyState>
          </div>
        ) : (
          questions.map((question, position) => (
            <div key={question.id} className="vmt-card vmt-stack">
              {editingId === question.id ? (
                <QuestionForm
                  initial={{ text: question.text, hint: question.hint, answer_seconds: question.answer_seconds ?? '' }}
                  onSave={handleEdit}
                  onCancel={() => setEditingId(null)}
                  saving={saving}
                  errors={formErrors}
                  submitLabel="Save question"
                />
              ) : (
                <div className="vmt-row" style={{ alignItems: 'flex-start', flexWrap: 'nowrap' }}>
                  <span className="vmt-step-num" aria-hidden="true">
                    {question.order}
                  </span>
                  <div className="vmt-stack vmt-stack-sm" style={{ flex: 1, minWidth: 0 }}>
                    <p className="body" style={{ fontWeight: 500 }}>
                      {question.text}
                    </p>
                    {question.hint && <p className="body-sm vmt-muted">Hint: {question.hint}</p>}
                    <span className="vmt-meta">Speaking time {formatDuration(question.time_limit)}</span>
                  </div>
                  {!archived && (
                    <div className="vmt-row vmt-row-tight" style={{ flexWrap: 'nowrap' }}>
                      <button
                        type="button"
                        className="vmt-icon-btn vmt-icon-btn-sm"
                        onClick={() => move(position, -1)}
                        disabled={position === 0}
                        aria-label={`Move question ${question.order} up`}
                      >
                        <ChevronUp className="vmt-icon" aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        className="vmt-icon-btn vmt-icon-btn-sm"
                        onClick={() => move(position, 1)}
                        disabled={position === questions.length - 1}
                        aria-label={`Move question ${question.order} down`}
                      >
                        <ChevronDown className="vmt-icon" aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        className="vmt-icon-btn vmt-icon-btn-sm"
                        onClick={() => {
                          setFormErrors({});
                          setEditingId(question.id);
                        }}
                        aria-label={`Edit question ${question.order}`}
                      >
                        <Pencil className="vmt-icon" aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        className="vmt-icon-btn vmt-icon-btn-sm"
                        onClick={() => setConfirmDelete(question)}
                        aria-label={`Delete question ${question.order}`}
                      >
                        <Trash2 className="vmt-icon" aria-hidden="true" />
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </section>

      {!archived && editingId === null && (
        <section className="vmt-card vmt-stack" aria-labelledby="add-title">
          <h2 id="add-title" className="title-sm">
            Add a question
          </h2>
          <QuestionForm initial={EMPTY_QUESTION} onSave={handleAdd} saving={saving} errors={formErrors} submitLabel="Add question" />
        </section>
      )}

      <Modal
        open={Boolean(confirmDelete)}
        title={`Delete question ${confirmDelete?.order}?`}
        description="Saved student answers keep their copy of the question."
        onClose={() => setConfirmDelete(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
            <Button variant="danger" loading={saving} onClick={handleDelete}>
              Delete question
            </Button>
          </>
        }
      />
    </>
  );
}
