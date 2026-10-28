import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowRight, CircleCheck, Flag, LogOut, Send, Timer } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import Alert from '../../components/Alert';
import AudioRecorder from '../../components/AudioRecorder';
import Brand from '../../components/Brand';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import Modal from '../../components/Modal';
import { getErrorMessage } from '../../services/api';
import { getAttempt, submitAttempt, uploadAnswer } from '../../services/testService';
import { formatDuration, formatScore } from '../../utils/formatters';

/**
 * The speaking test, one question at a time:
 * prep (thinking time) -> record -> saving (scoring) -> saved -> next question ... -> finish.
 */
export default function SpeakingTest() {
  const { attemptId } = useParams();
  const navigate = useNavigate();

  const [attempt, setAttempt] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState('loading'); // loading | prep | record | saving | saved | finishing
  const [prepLeft, setPrepLeft] = useState(0);
  const [recording, setRecording] = useState(null);
  const [recorderKey, setRecorderKey] = useState(0);
  const [lastAnswer, setLastAnswer] = useState(null);
  const [error, setError] = useState('');
  const [exitOpen, setExitOpen] = useState(false);
  const [notice, setNotice] = useState('');

  const questions = useMemo(() => attempt?.questions || [], [attempt]);
  const question = questions[index];
  const answeredCount = questions.filter((item) => item.answered).length;
  const allAnswered = questions.length > 0 && answeredCount === questions.length;

  const beginQuestion = useCallback((nextIndex, prepSeconds) => {
    setIndex(nextIndex);
    setRecording(null);
    setLastAnswer(null);
    setError('');
    setRecorderKey((key) => key + 1);
    setPrepLeft(prepSeconds);
    setPhase(prepSeconds > 0 ? 'prep' : 'record');
  }, []);

  // Load the attempt and jump to the first unanswered question.
  useEffect(() => {
    let active = true;
    getAttempt(attemptId)
      .then((data) => {
        if (!active) return;
        if (data.status !== 'in_progress') {
          navigate(`/student/results/${data.id}`, { replace: true });
          return;
        }
        setAttempt(data);
        const firstOpen = data.questions.findIndex((item) => !item.answered);
        if (firstOpen === -1) {
          setIndex(Math.max(0, data.questions.length - 1));
          setPhase('saved');
        } else {
          beginQuestion(firstOpen, data.test.prep_seconds);
        }
      })
      .catch((err) => active && setLoadError(getErrorMessage(err, 'This test could not be loaded.')));
    return () => {
      active = false;
    };
  }, [attemptId, navigate, beginQuestion]);

  // Thinking-time countdown.
  useEffect(() => {
    if (phase !== 'prep') return undefined;
    if (prepLeft <= 0) {
      setPhase('record');
      return undefined;
    }
    const timer = setTimeout(() => setPrepLeft((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [phase, prepLeft]);

  // Warn before closing the tab while an unsaved recording exists.
  useEffect(() => {
    const unsaved = (phase === 'record' && recording) || phase === 'saving';
    if (!unsaved) return undefined;
    const warn = (event) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [phase, recording]);

  const handleSubmitAnswer = async () => {
    if (!recording || !question) return;
    setPhase('saving');
    setError('');
    try {
      const answer = await uploadAnswer(attempt.id, {
        questionId: question.id,
        blob: recording.blob,
        durationSeconds: recording.duration,
      });
      setAttempt((current) => ({
        ...current,
        questions: current.questions.map((item) => (item.id === question.id ? { ...item, answered: true } : item)),
      }));
      setLastAnswer(answer);
      setNotice('');
      setPhase('saved');
    } catch (err) {
      if (err.response?.status === 404) {
        // The teacher removed this question while it was open: reload the test and carry on.
        try {
          const fresh = await getAttempt(attempt.id);
          if (fresh.status !== 'in_progress') {
            navigate(`/student/results/${fresh.id}`, { replace: true });
            return;
          }
          setAttempt(fresh);
          const nextOpen = fresh.questions.findIndex((item) => !item.answered);
          if (nextOpen === -1) {
            setIndex(Math.max(0, fresh.questions.length - 1));
            setPhase('saved');
          } else {
            beginQuestion(nextOpen, fresh.test.prep_seconds);
          }
          setNotice('Your teacher removed that question from the test. Your other answers are saved, so carry on.');
          return;
        } catch {
          /* show the normal message below */
        }
      }
      setError(getErrorMessage(err, 'Your answer could not be saved. Please submit it again.'));
      if (err.response?.status === 422) {
        // The recording itself was the problem: ask for a new one.
        setRecording(null);
        setRecorderKey((key) => key + 1);
      }
      setPhase('record');
    }
  };

  const handleNext = () => {
    const nextOpen = questions.findIndex((item) => !item.answered);
    if (nextOpen !== -1) beginQuestion(nextOpen, attempt.test.prep_seconds);
  };

  const handleFinish = async () => {
    setPhase('finishing');
    setError('');
    try {
      await submitAttempt(attempt.id);
      navigate(`/student/results/${attempt.id}`, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, 'Your results could not be prepared. Please try again.'));
      setPhase('saved');
      // A question may have been added to the test since it was opened: load it so it can be answered.
      getAttempt(attempt.id)
        .then((fresh) => fresh.status === 'in_progress' && setAttempt(fresh))
        .catch(() => {});
    }
  };

  if (loadError) {
    return (
      <div className="vmt-focus">
        <div className="vmt-focus-main">
          <Alert tone="danger" title="Test not available">
            {loadError}
          </Alert>
          <Button to="/student" variant="secondary">
            Back to dashboard
          </Button>
        </div>
      </div>
    );
  }
  if (!attempt || phase === 'loading') return <LoadingSpinner fullScreen label="Loading your test…" />;

  return (
    <div className="vmt-focus">
      <header className="vmt-focus-bar">
        <Brand to="/student" />
        <span className="label vmt-hide-sm">{attempt.test.title}</span>
        <Button variant="on-navy" size="sm" icon={LogOut} onClick={() => setExitOpen(true)}>
          Exit
        </Button>
      </header>

      <main className="vmt-focus-main">
        <div className="vmt-stack vmt-stack-sm">
          <div className="vmt-row vmt-row-between">
            <span className="label">
              Question {question?.order ?? index + 1} of {questions.length}
            </span>
            <span className="caption vmt-muted">
              {answeredCount} of {questions.length} answered
            </span>
          </div>
          <div className="vmt-steps" aria-hidden="true">
            {questions.map((item, position) => (
              <span
                key={item.id}
                className={`vmt-step${item.answered ? ' is-done' : ''}${position === index && !item.answered ? ' is-current' : ''}`}
              />
            ))}
          </div>
        </div>

        {notice && <Alert tone="info">{notice}</Alert>}

        {phase === 'finishing' && <LoadingSpinner label="Preparing your results…" />}

        {phase !== 'finishing' && question && !(phase === 'saved' && allAnswered && !lastAnswer) && (
          <section className="vmt-card vmt-question" aria-live="polite">
            <span className="overline">Question {question.order}</span>
            <p className="vmt-question-text">{question.text}</p>
            {question.hint && <p className="body-sm vmt-muted">Hint: {question.hint}</p>}
            <div className="vmt-chips">
              <span className="vmt-chip">
                <Timer className="vmt-icon-sm" aria-hidden="true" /> Speak for up to {formatDuration(question.time_limit)}
              </span>
            </div>
          </section>
        )}

        {phase === 'prep' && (
          <div className="vmt-countdown" role="timer" aria-live="off">
            <span className="overline vmt-teal">Thinking time</span>
            <span className="vmt-timer">{formatDuration(prepLeft)}</span>
            <span className="body-sm vmt-muted">Plan your answer. The recorder opens when the time is up.</span>
            <Button variant="secondary" onClick={() => setPhase('record')}>
              I'm ready to speak
            </Button>
          </div>
        )}

        {(phase === 'record' || phase === 'saving') && question && (
          <div className="vmt-card vmt-stack vmt-stack-lg">
            <AudioRecorder
              key={`${question.id}-${recorderKey}`}
              maxSeconds={question.time_limit}
              onChange={setRecording}
              disabled={phase === 'saving'}
            />
            {error && <Alert tone="danger">{error}</Alert>}
            <Button block icon={Send} onClick={handleSubmitAnswer} disabled={!recording} loading={phase === 'saving'}>
              {phase === 'saving' ? 'Scoring your answer…' : 'Submit answer'}
            </Button>
            {phase === 'saving' && (
              <p className="body-sm vmt-muted" style={{ textAlign: 'center' }}>
                This usually takes a few seconds.
              </p>
            )}
          </div>
        )}

        {phase === 'saved' && (
          <div className="vmt-card vmt-stack vmt-stack-lg" style={{ alignItems: 'center', textAlign: 'center' }}>
            <span className="vmt-empty-icon" aria-hidden="true">
              <CircleCheck className="vmt-icon-lg" />
            </span>
            {lastAnswer ? (
              <div className="vmt-stack vmt-stack-sm">
                <h2 className="title-md">Answer saved</h2>
                <p className="body-sm vmt-muted">
                  Score for this answer: <strong className="vmt-num">{formatScore(lastAnswer.overall)}</strong>. Your full
                  feedback is on the results page.
                </p>
              </div>
            ) : (
              <h2 className="title-md">All your answers are saved</h2>
            )}
            {error && <Alert tone="danger">{error}</Alert>}
            {allAnswered ? (
              <Button icon={Flag} onClick={handleFinish}>
                Finish test and see results
              </Button>
            ) : (
              <Button iconRight={ArrowRight} onClick={handleNext}>
                Next question
              </Button>
            )}
          </div>
        )}
      </main>

      <Modal
        open={exitOpen}
        title="Leave the test?"
        description="Your saved answers are kept. You can continue this test later from your dashboard."
        onClose={() => setExitOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setExitOpen(false)}>
              Stay
            </Button>
            <Button variant="danger" onClick={() => navigate('/student')}>
              Leave test
            </Button>
          </>
        }
      />
    </div>
  );
}
