import { useCallback, useEffect, useState } from 'react';
import { MessageSquare, RefreshCw, Search, Send, Trash2 } from 'lucide-react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import Alert from '../../components/Alert';
import AnswerDetails from '../../components/AnswerDetails';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import LoadingSpinner from '../../components/LoadingSpinner';
import Modal from '../../components/Modal';
import PageHeader from '../../components/PageHeader';
import ScoreRing from '../../components/ScoreRing';
import SkillBar from '../../components/SkillBar';
import StatusBadge from '../../components/StatusBadge';
import TextField from '../../components/TextField';
import { deleteAttempt, getAttempt, getAttempts, getEvaluationConfig, rescoreAnswer, reviewAttempt } from '../../services/adminService';
import { getErrorMessage, getFieldErrors } from '../../services/api';
import { DEFAULT_WEIGHTS, PAGE_SIZE, SKILLS } from '../../utils/constants';
import { formatDateTime, formatScore, headlineFor, levelLabel, overallFromSkills } from '../../utils/formatters';

const QUEUE_TABS = [
  { value: 'needs_review', label: 'Needs review' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'scored', label: 'Auto-scored' },
  { value: '', label: 'All' },
];

/** "Delete this result?" dialog, shared by the queue and the review page. */
function DeleteResultModal({ attempt, deleting, onCancel, onConfirm }) {
  return (
    <Modal
      open={Boolean(attempt)}
      title={`Delete ${attempt?.student.full_name}'s result?`}
      description={`Their answers, recordings, scores and any review for "${attempt?.test.title}" are removed for good. They can take the test again if it's still published.`}
      onClose={onCancel}
      footer={
        <>
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="danger" icon={Trash2} loading={deleting} onClick={onConfirm}>
            Delete result
          </Button>
        </>
      }
    />
  );
}

// ---------------------------------------------------------------------------
// Review queue
// ---------------------------------------------------------------------------
function ReviewQueue() {
  const location = useLocation();
  const navigate = useNavigate();
  const [notice, setNotice] = useState(location.state?.notice || '');
  const [reloadKey, setReloadKey] = useState(0);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [status, setStatus] = useState('needs_review');
  const [searchText, setSearchText] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchText.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchText]);

  // A notice handed over by the review page (after a delete) is shown once, not again on refresh.
  useEffect(() => {
    if (location.state?.notice) navigate(location.pathname, { replace: true });
  }, [location, navigate]);

  useEffect(() => {
    let active = true;
    setData(null);
    setError('');
    getAttempts({ status: status || undefined, search: search || undefined, page, page_size: PAGE_SIZE })
      .then((response) => {
        if (!active) return;
        setData(response);
        // The page asked for no longer exists (its last row was removed): the server sent the last page.
        if (response.page && response.page !== page) setPage(response.page);
      })
      .catch((err) => active && setError(getErrorMessage(err)));
    return () => {
      active = false;
    };
  }, [status, search, page, reloadKey]);

  const removeResult = async () => {
    const target = confirmDelete;
    setDeleting(true);
    try {
      await deleteAttempt(target.id);
      setNotice(`${target.student.full_name}'s result for "${target.test.title}" was deleted.`);
      setReloadKey((key) => key + 1);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDeleting(false);
      setConfirmDelete(null);
    }
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;

  return (
    <>
      <PageHeader
        overline="Reviews"
        title="Review queue"
        subtitle="Tests flagged for a teacher: low scores, very short answers, unclear audio or off-topic answers."
      />

      <div className="vmt-row vmt-row-between" style={{ alignItems: 'flex-end' }}>
        <div className="vmt-tabs" role="tablist" aria-label="Filter by status">
          {QUEUE_TABS.map((tab) => (
            <button
              key={tab.label}
              type="button"
              role="tab"
              aria-selected={status === tab.value}
              className={`vmt-tab${status === tab.value ? ' is-active' : ''}`}
              onClick={() => {
                setStatus(tab.value);
                setPage(1);
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="vmt-field" style={{ flex: '0 1 320px' }}>
          <label className="vmt-label sr-only" htmlFor="review-search">
            Search
          </label>
          <div className="vmt-input-wrap has-icon">
            <Search className="vmt-icon vmt-input-icon" aria-hidden="true" />
            <input
              id="review-search"
              className="vmt-input"
              type="search"
              placeholder="Student or test"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
            />
          </div>
        </div>
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
          <EmptyState icon={MessageSquare} title={status === 'needs_review' ? 'Nothing to review' : 'No tests found'}>
            {status === 'needs_review' ? 'All flagged tests have been reviewed.' : 'Try another filter or search.'}
          </EmptyState>
        </div>
      )}

      {data && data.results.length > 0 && (
        <>
          <div className="vmt-table-wrap">
            <table className="vmt-table" style={{ minWidth: 860 }}>
              <thead>
                <tr>
                  <th scope="col">Student</th>
                  <th scope="col">Test</th>
                  <th scope="col" className="is-num">Score</th>
                  <th scope="col">Why it was flagged</th>
                  <th scope="col">Submitted</th>
                  <th scope="col">Status</th>
                  <th scope="col" className="is-actions">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((attempt) => (
                  <tr key={attempt.id}>
                    <td>
                      <span className="vmt-cell-main">{attempt.student.full_name}</span>
                      <br />
                      <span className="caption vmt-muted">{attempt.student.email}</span>
                    </td>
                    <td>{attempt.test.title}</td>
                    <td className="is-num vmt-cell-main">{formatScore(attempt.overall)}</td>
                    <td style={{ maxWidth: 260 }}>
                      {attempt.review_reasons?.length ? (
                        <span className="body-sm">
                          {attempt.review_reasons[0]}
                          {attempt.review_reasons.length > 1 && (
                            <span className="vmt-muted"> +{attempt.review_reasons.length - 1} more</span>
                          )}
                        </span>
                      ) : (
                        <span className="vmt-muted">—</span>
                      )}
                    </td>
                    <td>{formatDateTime(attempt.submitted_at)}</td>
                    <td>
                      <StatusBadge kind="attempt" status={attempt.status} />
                    </td>
                    <td className="is-actions">
                      <div className="vmt-row vmt-row-tight" style={{ justifyContent: 'flex-end', flexWrap: 'nowrap' }}>
                        <Button size="sm" variant={attempt.status === 'needs_review' ? 'primary' : 'secondary'} to={`/admin/reviews/${attempt.id}`}>
                          {attempt.status === 'needs_review' ? 'Review' : 'Open'}
                        </Button>
                        <button
                          type="button"
                          className="vmt-icon-btn vmt-icon-btn-sm"
                          onClick={() => setConfirmDelete(attempt)}
                          aria-label={`Delete ${attempt.student.full_name}'s result`}
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
          {totalPages > 1 && (
            <div className="vmt-pagination">
              <span className="body-sm vmt-muted">
                Page {page} of {totalPages}
              </span>
              <div className="vmt-row vmt-row-tight">
                <Button size="sm" variant="secondary" disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <Button size="sm" variant="secondary" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
      <DeleteResultModal attempt={confirmDelete} deleting={deleting} onCancel={() => setConfirmDelete(null)} onConfirm={removeResult} />
    </>
  );
}

// ---------------------------------------------------------------------------
// Review one attempt
// ---------------------------------------------------------------------------
function formFromAttempt(attempt) {
  return {
    fluency: attempt.fluency ?? '',
    pronunciation: attempt.pronunciation ?? '',
    grammar: attempt.grammar ?? '',
    strength1: attempt.strengths?.[0] || '',
    strength2: attempt.strengths?.[1] || '',
    tip: attempt.tip || '',
    next_step: attempt.next_step || '',
    reviewer_note: attempt.reviewer_note || '',
    notify_student: true,
  };
}

function ReviewDetail({ attemptId }) {
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [form, setForm] = useState(null);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [rescoringId, setRescoringId] = useState(null);

  const load = useCallback(async () => {
    try {
      const [data, config] = await Promise.all([getAttempt(attemptId), getEvaluationConfig().catch(() => null)]);
      setAttempt(data);
      setForm(formFromAttempt(data));
      if (config?.weights) setWeights(config.weights);
    } catch (err) {
      setError(getErrorMessage(err, 'This test could not be loaded.'));
    }
  }, [attemptId]);

  useEffect(() => {
    load();
  }, [load]);

  const update = (field) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: '' }));
  };

  const handleRescore = async (answerId) => {
    setRescoringId(answerId);
    setError('');
    try {
      await rescoreAnswer(answerId);
      const fresh = await getAttempt(attemptId);
      setAttempt(fresh);
      // Show the new scores, but keep the feedback the admin has already typed.
      const { fluency, pronunciation, grammar } = formFromAttempt(fresh);
      setForm((current) => ({ ...current, fluency, pronunciation, grammar }));
    } catch (err) {
      setError(getErrorMessage(err, 'The answer could not be scored again.'));
    } finally {
      setRescoringId(null);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const found = {};
    SKILLS.forEach(({ key }) => {
      const value = Number(form[key]);
      if (form[key] === '' || !Number.isInteger(value) || value < 0 || value > 100) found[key] = 'Enter a whole number from 0 to 100.';
    });
    setErrors(found);
    if (Object.keys(found).length) return;

    setSaving(true);
    setError('');
    setResult(null);
    try {
      const response = await reviewAttempt(attempt.id, {
        fluency: Number(form.fluency),
        pronunciation: Number(form.pronunciation),
        grammar: Number(form.grammar),
        strengths: [form.strength1, form.strength2].map((text) => text.trim()).filter(Boolean),
        tip: form.tip.trim(),
        next_step: form.next_step.trim(),
        reviewer_note: form.reviewer_note.trim(),
        notify_student: form.notify_student,
      });
      setAttempt(response.attempt);
      setForm(formFromAttempt(response.attempt));
      // Remember whether an email was asked for: the form's checkbox is reset above.
      setResult({ ...response, notified: form.notify_student });
    } catch (err) {
      const fieldErrors = getFieldErrors(err);
      setErrors(fieldErrors);
      setError(getErrorMessage(err, 'The review could not be saved.'));
    } finally {
      setSaving(false);
    }
  };

  const removeResult = async () => {
    setDeleting(true);
    try {
      await deleteAttempt(attempt.id);
      navigate('/admin/reviews', { state: { notice: `${attempt.student.full_name}'s result for "${attempt.test.title}" was deleted.` } });
    } catch (err) {
      setError(getErrorMessage(err));
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  if (!attempt && error) {
    return (
      <>
        <PageHeader title="Review" back={{ to: '/admin/reviews', label: 'Review queue' }} />
        <Alert tone="danger">{error}</Alert>
      </>
    );
  }
  if (!attempt || !form) return <LoadingSpinner label="Loading the test…" />;

  const preview = overallFromSkills(form, weights);
  const isDemo = attempt.answers.some((answer) => answer.is_demo);

  return (
    <>
      <PageHeader
        back={{ to: '/admin/reviews', label: 'Review queue' }}
        overline="Review"
        title={attempt.student.full_name}
        subtitle={`${attempt.test.title} · ${levelLabel(attempt.student.level)} · submitted ${formatDateTime(attempt.submitted_at)}`}
        actions={
          <>
            <StatusBadge kind="attempt" status={attempt.status} />
            <Button size="sm" variant="secondary" icon={Trash2} onClick={() => setConfirmDelete(true)}>
              Delete result
            </Button>
          </>
        }
      />
      <DeleteResultModal
        attempt={confirmDelete ? attempt : null}
        deleting={deleting}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={removeResult}
      />

      {attempt.status === 'in_progress' && (
        <Alert tone="info" title="Not submitted yet">
          The student hasn't finished this test, so it can't be reviewed yet.
        </Alert>
      )}
      {attempt.review_reasons?.length > 0 && attempt.status !== 'reviewed' && (
        <Alert tone="warning" title="Why it was flagged">
          {attempt.review_reasons.join(' · ')}
        </Alert>
      )}
      {attempt.status === 'reviewed' && (
        <Alert tone="success" title={`Reviewed by ${attempt.reviewer_name || 'an admin'}`}>
          You can change the review and publish it again.
        </Alert>
      )}
      {isDemo && <Alert tone="warning">These answers were scored in demo mode (sample values).</Alert>}

      <div className="vmt-split">
        <div className="vmt-stack vmt-stack-lg">
          <div className="vmt-card vmt-row" style={{ gap: 'var(--space-4)' }}>
            <ScoreRing value={attempt.overall} size="sm" />
            <div className="vmt-stack" style={{ flex: '1 1 240px' }}>
              {SKILLS.map((skill) => (
                <SkillBar key={skill.key} label={skill.label} value={attempt[skill.key]} />
              ))}
            </div>
          </div>
          {attempt.summary && <p className="body vmt-muted">{attempt.summary}</p>}
          <section className="vmt-stack" aria-labelledby="answers-title">
            <h2 id="answers-title" className="title-md">
              Answers
            </h2>
            <div>
              {attempt.answers.map((answer) => (
                <AnswerDetails
                  key={answer.id}
                  answer={answer}
                  actions={
                    attempt.status !== 'in_progress' && (
                      <div>
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={RefreshCw}
                          loading={rescoringId === answer.id}
                          onClick={() => handleRescore(answer.id)}
                        >
                          Score this answer again
                        </Button>
                      </div>
                    )
                  }
                />
              ))}
            </div>
          </section>
        </div>

        {attempt.status !== 'in_progress' && (
          <form className="vmt-card vmt-form" onSubmit={handleSubmit} noValidate aria-labelledby="review-title">
            <h2 id="review-title" className="title-sm">
              Your review
            </h2>
            {result && (
              <Alert tone={result.email_sent || !result.notified ? 'success' : 'warning'} onClose={() => setResult(null)}>
                Review published.{' '}
                {result.email_sent ? 'The student has been emailed.' : result.notified ? 'The email could not be sent.' : ''}
              </Alert>
            )}
            {error && <Alert tone="danger">{error}</Alert>}
            <div className="vmt-grid-3">
              {SKILLS.map((skill) => (
                <TextField
                  key={skill.key}
                  label={skill.label}
                  type="number"
                  min={0}
                  max={100}
                  value={form[skill.key]}
                  onChange={update(skill.key)}
                  error={errors[skill.key]}
                />
              ))}
            </div>
            <div className="vmt-callout">
              <span className="overline">New overall score</span>
              <span className="title-md vmt-num">
                {formatScore(preview)} <span className="body-sm vmt-muted">{headlineFor(preview)}</span>
              </span>
            </div>
            <TextField label="Strength 1" value={form.strength1} onChange={update('strength1')} placeholder="You answered the question directly." />
            <TextField label="Strength 2" value={form.strength2} onChange={update('strength2')} />
            <TextField as="textarea" rows={2} label="Tip for next time" value={form.tip} onChange={update('tip')} error={errors.tip} />
            <TextField as="textarea" rows={2} label="Next step" value={form.next_step} onChange={update('next_step')} error={errors.next_step} />
            <TextField
              as="textarea"
              rows={3}
              label="Note to the student (optional)"
              value={form.reviewer_note}
              onChange={update('reviewer_note')}
              error={errors.reviewer_note}
              help="Shown on the student's results page and in the email."
            />
            <label className="vmt-check">
              <input type="checkbox" checked={form.notify_student} onChange={update('notify_student')} />
              Email the student when I publish
            </label>
            <Button type="submit" icon={Send} loading={saving} block>
              Publish review
            </Button>
          </form>
        )}
      </div>
    </>
  );
}

export default function ReviewAttempts() {
  const { attemptId } = useParams();
  return attemptId ? <ReviewDetail key={attemptId} attemptId={attemptId} /> : <ReviewQueue />;
}
