import { useEffect, useState } from 'react';
import { Check, Lightbulb, PlayCircle, RotateCcw, Target } from 'lucide-react';
import { useParams } from 'react-router-dom';
import Alert from '../../components/Alert';
import AnswerDetails from '../../components/AnswerDetails';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import PageHeader from '../../components/PageHeader';
import ScoreRing from '../../components/ScoreRing';
import SkillBar from '../../components/SkillBar';
import StatusBadge from '../../components/StatusBadge';
import { getErrorMessage } from '../../services/api';
import { getResult } from '../../services/resultService';
import { SKILLS } from '../../utils/constants';
import { formatDateTime, levelLabel } from '../../utils/formatters';

export default function TestResult() {
  const { attemptId } = useParams();
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    getResult(attemptId)
      .then((data) => active && setResult(data))
      .catch((err) => active && setError(getErrorMessage(err, 'These results could not be loaded.')));
    return () => {
      active = false;
    };
  }, [attemptId]);

  if (error) {
    return (
      <>
        <PageHeader title="Results" back={{ to: '/student/history', label: 'My results' }} />
        <Alert tone="danger">{error}</Alert>
      </>
    );
  }
  if (!result) return <LoadingSpinner label="Loading your results…" />;

  if (result.status === 'in_progress') {
    return (
      <>
        <PageHeader title={result.test.title} back={{ to: '/student/history', label: 'My results' }} />
        <Alert tone="info" title="This test isn't finished yet">
          Answer the remaining questions to see your results.
        </Alert>
        <div>
          <Button to={`/student/attempts/${result.id}`} icon={PlayCircle}>
            Continue test
          </Button>
        </div>
      </>
    );
  }

  const isDemo = result.answers.some((answer) => answer.is_demo);

  return (
    <>
      <PageHeader
        back={{ to: '/student/history', label: 'My results' }}
        overline="Your results"
        title={result.test.title}
        subtitle={`${levelLabel(result.test.level)} · Submitted ${formatDateTime(result.submitted_at)}`}
        actions={<StatusBadge kind="attempt" status={result.status} />}
      />

      {isDemo && (
        <Alert tone="warning" title="Demo scores">
          The app is running in demo mode, so these scores are sample values, not a real assessment.
        </Alert>
      )}
      {result.status === 'needs_review' && (
        <Alert tone="info" title="A teacher will review this test">
          Your scores may change after the review. We'll email you when it's done.
        </Alert>
      )}
      {result.status === 'reviewed' && (
        <Alert tone="success" title={`Reviewed by ${result.reviewer_name || 'your teacher'}`}>
          {result.reviewer_note || 'Your teacher has checked your answers and confirmed your scores.'}
        </Alert>
      )}

      <div className="vmt-split">
        <div className="vmt-card vmt-stack vmt-stack-lg">
          <div className="vmt-row" style={{ gap: 'var(--space-4)' }}>
            <ScoreRing value={result.overall} />
            <div className="vmt-stack vmt-stack-sm" style={{ flex: '1 1 220px' }}>
              <h2 className="title-lg">{result.headline || 'Results'}</h2>
              <p className="body vmt-muted">{result.summary}</p>
            </div>
          </div>
          <div className="vmt-stack">
            {SKILLS.map((skill) => (
              <SkillBar key={skill.key} label={skill.label} value={result[skill.key]} description={skill.description} />
            ))}
          </div>
        </div>

        <div className="vmt-stack">
          <div className="vmt-card vmt-stack">
            <h2 className="title-sm">What went well</h2>
            {result.strengths?.length ? (
              <ul className="vmt-checklist">
                {result.strengths.map((text, index) => (
                  <li key={`${index}-${text}`}>
                    <span className="vmt-check-icon" aria-hidden="true">
                      <Check className="vmt-icon-sm" />
                    </span>
                    {text}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="body-sm vmt-muted">Keep practising to build your strengths.</p>
            )}
          </div>
          {result.tip && (
            <div className="vmt-callout vmt-callout-warning">
              <span className="overline">
                <Lightbulb className="vmt-icon-sm" aria-hidden="true" style={{ verticalAlign: '-3px' }} /> Tip for next time
              </span>
              <span className="body-sm">{result.tip}</span>
            </div>
          )}
          {result.next_step && (
            <div className="vmt-callout">
              <span className="overline">
                <Target className="vmt-icon-sm" aria-hidden="true" style={{ verticalAlign: '-3px' }} /> Next step
              </span>
              <span className="body-sm">{result.next_step}</span>
            </div>
          )}
        </div>
      </div>

      <section className="vmt-stack" aria-labelledby="answers-title">
        <h2 id="answers-title" className="title-md">
          Your answers
        </h2>
        <div>
          {result.answers.map((answer) => (
            <AnswerDetails key={answer.id} answer={answer} />
          ))}
        </div>
      </section>

      <div className="vmt-row">
        {result.test.allow_retake && (
          <Button to={`/student/tests/${result.test.id}`} icon={RotateCcw} variant="secondary">
            Take this test again
          </Button>
        )}
        <Button to="/student">Choose another test</Button>
      </div>
    </>
  );
}
