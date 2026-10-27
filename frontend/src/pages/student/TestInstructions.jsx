import { useEffect, useState } from 'react';
import { Check, Clock, Headphones, ListChecks, Mic, PlayCircle, Timer } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import Alert from '../../components/Alert';
import AudioRecorder from '../../components/AudioRecorder';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import { getErrorMessage } from '../../services/api';
import { getTest, startAttempt } from '../../services/testService';
import { MIC_CHECK_SECONDS } from '../../utils/constants';
import { formatDuration, formatScore, levelLabel, pluralize } from '../../utils/formatters';

const TIPS = [
  'Find a quiet place and keep your phone or laptop close to you.',
  'Check your microphone below before you start.',
  'Each question gives you thinking time first, then time to speak.',
  'You can listen to each answer and record it again before you submit it.',
  'If you leave, your saved answers are kept and you can continue later.',
];

export default function TestInstructions() {
  const { testId } = useParams();
  const navigate = useNavigate();
  const [test, setTest] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [startError, setStartError] = useState('');
  const [starting, setStarting] = useState(false);
  const [micChecked, setMicChecked] = useState(false);

  useEffect(() => {
    let active = true;
    getTest(testId)
      .then((data) => active && setTest(data))
      .catch((err) => active && setLoadError(getErrorMessage(err, 'This test could not be loaded.')));
    return () => {
      active = false;
    };
  }, [testId]);

  const handleStart = async () => {
    setStarting(true);
    setStartError('');
    try {
      const attempt = await startAttempt(test.id);
      navigate(`/student/attempts/${attempt.id}`);
    } catch (err) {
      setStartError(getErrorMessage(err, 'The test could not start. Please try again.'));
      setStarting(false);
    }
  };

  if (loadError) {
    return (
      <>
        <PageHeader title="Test not found" back={{ to: '/student', label: 'All tests' }} />
        <Alert tone="danger">{loadError}</Alert>
      </>
    );
  }
  if (!test) return <LoadingSpinner label="Loading the test…" />;

  const resuming = Boolean(test.in_progress_attempt_id);

  return (
    <>
      <PageHeader
        back={{ to: '/student', label: 'All tests' }}
        overline="Mock test"
        title={test.title}
        subtitle={test.description || 'A short speaking test with exam-style questions.'}
        actions={<StatusBadge tone="ready">{levelLabel(test.level)}</StatusBadge>}
      />

      <div className="vmt-grid">
        <div className="vmt-card vmt-stat">
          <span className="vmt-stat-label">Questions</span>
          <span className="vmt-stat-value">{test.question_count}</span>
        </div>
        <div className="vmt-card vmt-stat">
          <span className="vmt-stat-label">Thinking time</span>
          <span className="vmt-stat-value">{formatDuration(test.prep_seconds)}</span>
          <span className="vmt-meta">before each answer</span>
        </div>
        <div className="vmt-card vmt-stat">
          <span className="vmt-stat-label">Speaking time</span>
          <span className="vmt-stat-value">{formatDuration(test.answer_seconds)}</span>
          <span className="vmt-meta">for each answer</span>
        </div>
        <div className="vmt-card vmt-stat">
          <span className="vmt-stat-label">Total time</span>
          <span className="vmt-stat-value">~{test.estimated_minutes} min</span>
          {test.my_best_score !== null && <span className="vmt-stat-sub">Your best: {formatScore(test.my_best_score)}</span>}
        </div>
      </div>

      <div className="vmt-split">
        <div className="vmt-card vmt-stack">
          <div className="vmt-row vmt-row-tight">
            <ListChecks className="vmt-icon vmt-teal" aria-hidden="true" />
            <h2 className="title-sm">Before you start</h2>
          </div>
          <ul className="vmt-checklist">
            {TIPS.map((tip) => (
              <li key={tip}>
                <span className="vmt-check-icon" aria-hidden="true">
                  <Check className="vmt-icon-sm" />
                </span>
                {tip}
              </li>
            ))}
          </ul>
          <div className="vmt-chips">
            <span className="vmt-chip">
              <Clock className="vmt-icon-sm" aria-hidden="true" /> {pluralize(test.question_count, 'question')}
            </span>
            <span className="vmt-chip">
              <Timer className="vmt-icon-sm" aria-hidden="true" /> Up to {formatDuration(test.answer_seconds)} per answer
            </span>
          </div>
        </div>

        <div className="vmt-card vmt-stack">
          <div className="vmt-row vmt-row-tight">
            <Headphones className="vmt-icon vmt-teal" aria-hidden="true" />
            <h2 className="title-sm">Microphone check</h2>
          </div>
          <p className="body-sm vmt-muted">
            Say a short sentence, then play it back. If you can hear yourself clearly, you're ready.
          </p>
          <AudioRecorder compact maxSeconds={MIC_CHECK_SECONDS} onChange={(result) => result && setMicChecked(true)} />
          {micChecked && <Alert tone="success">Your microphone works.</Alert>}
        </div>
      </div>

      {startError && <Alert tone="danger">{startError}</Alert>}

      <div className="vmt-banner">
        <div className="vmt-stack vmt-stack-sm">
          <span className="title-sm">
            {resuming ? 'You have already started this test.' : test.can_start ? 'Ready when you are.' : 'You have completed this test.'}
          </span>
          <span className="body-sm vmt-muted">
            {resuming
              ? 'Continue to answer the remaining questions.'
              : test.can_start
                ? 'The first question appears as soon as you start.'
                : 'This test can only be taken once. Choose another test from your dashboard.'}
          </span>
        </div>
        {(resuming || test.can_start) && (
          <Button onClick={handleStart} loading={starting} icon={resuming ? PlayCircle : Mic}>
            {resuming ? 'Continue test' : 'Start test'}
          </Button>
        )}
      </div>
    </>
  );
}
