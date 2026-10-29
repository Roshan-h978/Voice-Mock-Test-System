import { useEffect, useState } from 'react';
import { ArrowRight, BookOpenCheck, ClipboardList, Mic, RotateCcw, Send, Shuffle, Sparkles } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import Alert from '../../components/Alert';
import { AnswerFeedback } from '../../components/AnswerDetails';
import AudioRecorder from '../../components/AudioRecorder';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import PageHeader from '../../components/PageHeader';
import ScoreRing from '../../components/ScoreRing';
import SkillBar from '../../components/SkillBar';
import { getErrorMessage } from '../../services/api';
import { getPracticeHistory, getPracticeQuestion, getPracticeTopics, submitPracticeAnswer } from '../../services/learningService';
import { SKILLS } from '../../utils/constants';
import { formatDuration, formatScore, headlineFor, timeAgo } from '../../utils/formatters';

const SOURCES = [
  { value: 'ai', label: 'New question on a topic', icon: Sparkles },
  { value: 'tests', label: 'Question from the tests', icon: ClipboardList },
];

/** One question, one recording, feedback straight away. Practice answers never count in test results. */
export default function QuickPractice() {
  const location = useLocation();
  const [topics, setTopics] = useState([]);
  const [source, setSource] = useState('ai');
  const [topic, setTopic] = useState('');
  const [question, setQuestion] = useState(location.state?.question || null);
  const [recording, setRecording] = useState(null);
  const [recorderKey, setRecorderKey] = useState(0);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(''); // '' | 'question' | 'scoring'
  const [error, setError] = useState('');
  const [history, setHistory] = useState(null);

  useEffect(() => {
    getPracticeTopics()
      .then(setTopics)
      .catch(() => setTopics([]));
  }, []);

  useEffect(() => {
    let active = true;
    getPracticeHistory({ page_size: 5 })
      .then((data) => active && setHistory(data))
      .catch(() => active && setHistory({ count: 0, results: [] }));
    return () => {
      active = false;
    };
  }, [result]);

  const freshRecorder = () => {
    setRecording(null);
    setRecorderKey((key) => key + 1);
  };

  const fetchQuestion = async () => {
    setBusy('question');
    setError('');
    setResult(null);
    try {
      setQuestion(await getPracticeQuestion({ source, topic: source === 'ai' ? topic : '' }));
      freshRecorder();
    } catch (err) {
      setError(getErrorMessage(err, 'We could not get a question. Try again.'));
    } finally {
      setBusy('');
    }
  };

  const submit = async () => {
    if (!recording || !question) return;
    setBusy('scoring');
    setError('');
    try {
      setResult(await submitPracticeAnswer({ question, blob: recording.blob, durationSeconds: recording.duration }));
    } catch (err) {
      setError(getErrorMessage(err, 'Your answer could not be scored. Please submit it again.'));
      if (err.response?.status === 422) freshRecorder();
    } finally {
      setBusy('');
    }
  };

  const tryAgain = () => {
    setResult(null);
    freshRecorder();
  };

  return (
    <>
      <PageHeader
        overline="Practice"
        title="Quick practice"
        subtitle="Answer one question and get feedback straight away. Practice answers don't count in your test results."
      />

      <section className="vmt-card vmt-stack vmt-stack-lg" aria-labelledby="choose-title">
        <h2 id="choose-title" className="title-sm">
          Choose your question
        </h2>
        <div className="vmt-choice-row" role="radiogroup" aria-label="Where the question comes from">
          {SOURCES.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={source === value}
              className={`vmt-choice${source === value ? ' is-active' : ''}`}
              onClick={() => setSource(value)}
            >
              <Icon className="vmt-icon" aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>
        {source === 'ai' && topics.length > 0 && (
          <div className="vmt-stack vmt-stack-sm">
            <span className="label" id="topic-label">
              Topic
            </span>
            <div className="vmt-topic-chips" role="radiogroup" aria-labelledby="topic-label">
              {[{ value: '', label: 'Any topic' }, ...topics].map((item) => (
                <button
                  key={item.value || 'any'}
                  type="button"
                  role="radio"
                  aria-checked={topic === item.value}
                  className={`vmt-topic-chip${topic === item.value ? ' is-active' : ''}`}
                  onClick={() => setTopic(item.value)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        )}
        <div>
          <Button icon={question ? Shuffle : ArrowRight} loading={busy === 'question'} onClick={fetchQuestion} variant={question ? 'secondary' : 'primary'}>
            {question ? 'Get a different question' : 'Get a question'}
          </Button>
        </div>
      </section>

      {error && <Alert tone="danger">{error}</Alert>}

      {question && (
        <section className="vmt-card vmt-stack vmt-stack-lg vmt-practice-question" aria-labelledby="practice-question">
          <div className="vmt-row vmt-row-between">
            <span className="vmt-badge vmt-badge-ready">{question.topic_label || 'Practice'}</span>
            <span className="caption vmt-muted">Speak for up to {formatDuration(question.time_limit)}</span>
          </div>
          <h2 id="practice-question" className="vmt-question-text">
            {question.question_text}
          </h2>
          {question.hint && <p className="body-sm vmt-muted">Ideas: {question.hint}</p>}
          {question.is_demo && <p className="caption vmt-muted">Demo mode: this question is from the built-in bank.</p>}

          {!result && (
            <>
              <AudioRecorder key={recorderKey} maxSeconds={question.time_limit} onChange={setRecording} disabled={busy === 'scoring'} />
              <Button block icon={Send} onClick={submit} disabled={!recording} loading={busy === 'scoring'}>
                {busy === 'scoring' ? 'Scoring your answer…' : 'Get my feedback'}
              </Button>
            </>
          )}
        </section>
      )}

      {result && (
        <section className="vmt-stack vmt-stack-lg" aria-labelledby="practice-result">
          <div className="vmt-card vmt-practice-score">
            <ScoreRing value={result.overall} size="sm" label="Score for this answer" />
            <div className="vmt-stack vmt-stack-sm" style={{ flex: '1 1 260px' }}>
              <h2 id="practice-result" className="title-md">
                {headlineFor(result.overall)}
              </h2>
              {SKILLS.map((skill) => (
                <SkillBar key={skill.key} label={skill.label} value={result[skill.key]} />
              ))}
            </div>
          </div>
          <div className="vmt-card vmt-stack">
            <AnswerFeedback answer={result} label="Your practice recording" />
          </div>
          <div className="vmt-row">
            <Button variant="secondary" icon={RotateCcw} onClick={tryAgain}>
              Answer this question again
            </Button>
            <Button iconRight={ArrowRight} onClick={fetchQuestion} loading={busy === 'question'}>
              Next question
            </Button>
            {result.corrections?.length > 0 && (
              <Button variant="ghost" icon={BookOpenCheck} to="/student/notebook">
                See my notebook
              </Button>
            )}
          </div>
        </section>
      )}

      <section className="vmt-stack" aria-labelledby="recent-title">
        <h2 id="recent-title" className="title-md">
          Recent practice
        </h2>
        {history && history.results.length === 0 && (
          <div className="vmt-card">
            <EmptyState icon={Mic} title="No practice yet">
              Get a question above and record your first answer.
            </EmptyState>
          </div>
        )}
        {history && history.results.length > 0 && (
          <ul className="vmt-practice-list">
            {history.results.map((item) => (
              <li key={item.id}>
                <Link to={`/student/practice/${item.id}`} className="vmt-practice-item">
                  <span className="vmt-practice-score-chip vmt-num">{formatScore(item.overall)}</span>
                  <span className="vmt-practice-item-text">
                    <span className="vmt-cell-main">{item.question_text}</span>
                    <span className="caption vmt-muted">
                      {item.topic_label || (item.source === 'tests' ? 'From the tests' : 'Practice')}, {timeAgo(item.created_at)}
                    </span>
                  </span>
                  <ArrowRight className="vmt-icon vmt-practice-arrow" aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ul>
        )}
        {history && history.count > history.results.length && (
          <p className="body-sm vmt-muted">
            Showing your latest {history.results.length} of {history.count} practice answers. Your scores over time are on{' '}
            <Link to="/student/progress" className="vmt-link">
              My progress
            </Link>
            .
          </p>
        )}
      </section>
    </>
  );
}
