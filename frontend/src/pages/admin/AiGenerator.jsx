import { useEffect, useState } from 'react';
import { ListChecks, Plus, RefreshCw, Save, Sparkles, Trash2 } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import Alert from '../../components/Alert';
import Button from '../../components/Button';
import PageHeader from '../../components/PageHeader';
import TextField from '../../components/TextField';
import { addQuestions, aiCreateTest, aiWrite, getTests } from '../../services/adminService';
import { getErrorMessage, getFieldErrors } from '../../services/api';
import { LEVELS } from '../../utils/constants';
import { formatDuration, pluralize } from '../../utils/formatters';

const STYLES = [
  { value: 'mixed', label: 'Mixed' },
  { value: 'experience', label: 'Personal experience' },
  { value: 'opinion', label: 'Opinion and reasons' },
  { value: 'describe', label: 'Describe and explain' },
  { value: 'compare', label: 'Compare' },
  { value: 'problem', label: 'Problem and solution' },
  { value: 'roleplay', label: 'Role play' },
];
const TOPIC_IDEAS = ['Daily routines', 'Travel and holidays', 'Job interview', 'Technology in everyday life', 'Protecting the environment', 'Festivals in Nepal'];
const COUNTS = [3, 4, 5, 6, 8, 10];
const TIMES = [30, 45, 60, 90, 120];
const MAX_QUESTIONS = 20;

/** Admin page: the AI writes a whole speaking test from a topic; the admin checks it, then saves it. */
export default function AiGenerator() {
  const [searchParams] = useSearchParams();
  const [settings, setSettings] = useState({ topic: '', level: 'intermediate', count: 5, answer_seconds: 60, style: 'mixed' });
  const [draft, setDraft] = useState(null); // { title, description, questions: [{ text, hint }], is_demo }
  const [busy, setBusy] = useState(''); // '' | 'writing' | 'rewrite-<n>' | 'adding' | 'saving'
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [tests, setTests] = useState([]);
  const [destination, setDestination] = useState(searchParams.get('test') ? 'existing' : 'new');
  const [targetTest, setTargetTest] = useState(searchParams.get('test') || '');
  const [saved, setSaved] = useState(null); // { id, title, added }
  // Every question suggested on this page so far: new suggestions never repeat one (even after Remove or Rewrite).
  const [seen, setSeen] = useState([]);
  const remember = (questions) => setSeen((list) => [...list, ...questions.map((item) => item.text)].slice(-60));

  useEffect(() => {
    getTests()
      .then((list) => {
        const editable = list.filter((test) => test.status !== 'archived');
        setTests(editable);
        const preset = editable.find((test) => String(test.id) === searchParams.get('test'));
        if (preset) setSettings((current) => ({ ...current, topic: current.topic || preset.title, level: preset.level, answer_seconds: preset.answer_seconds }));
      })
      .catch(() => setTests([]));
  }, [searchParams]);

  const set = (field) => (event) => setSettings((current) => ({ ...current, [field]: event.target.value }));
  const request = (extra) => ({
    topic: settings.topic.trim(),
    level: settings.level,
    answer_seconds: Number(settings.answer_seconds),
    style: settings.style,
    test: destination === 'existing' && targetTest ? Number(targetTest) : null,
    ...extra,
  });

  const writeTest = async (event) => {
    event.preventDefault();
    if (settings.topic.trim().length < 3) {
      setFieldErrors({ topic: 'Describe the topic in a few words.' });
      return;
    }
    setBusy('writing');
    setError('');
    setFieldErrors({});
    setSaved(null);
    try {
      const data = await aiWrite(request({ count: Number(settings.count), with_title: true, exclude: seen }));
      remember(data.questions);
      setDraft({ ...data, level: settings.level, answer_seconds: Number(settings.answer_seconds) });
    } catch (err) {
      setFieldErrors(getFieldErrors(err));
      setError(getErrorMessage(err, 'The AI could not write the test right now. Try again in a minute.'));
    } finally {
      setBusy('');
    }
  };

  const oneMore = async (replaceIndex = null) => {
    setBusy(replaceIndex === null ? 'adding' : `rewrite-${replaceIndex}`);
    setError('');
    try {
      const current = draft.questions.map((item) => item.text);
      const data = await aiWrite(request({ count: 1, exclude: [...new Set([...seen, ...current])].slice(-60) }));
      const [question] = data.questions;
      remember(data.questions);
      setDraft((current) => ({
        ...current,
        questions:
          replaceIndex === null
            ? [...current.questions, question]
            : current.questions.map((item, index) => (index === replaceIndex ? question : item)),
      }));
    } catch (err) {
      setError(getErrorMessage(err, 'The AI could not write another question right now.'));
    } finally {
      setBusy('');
    }
  };

  const editQuestion = (index, field) => (event) => {
    const value = event.target.value;
    setDraft((current) => ({ ...current, questions: current.questions.map((item, position) => (position === index ? { ...item, [field]: value } : item)) }));
  };
  const removeQuestion = (index) => setDraft((current) => ({ ...current, questions: current.questions.filter((_, position) => position !== index) }));

  const usable = (draft?.questions || []).filter((item) => item.text.trim().length >= 5);
  const target = tests.find((test) => String(test.id) === String(targetTest));

  const save = async () => {
    setBusy('saving');
    setError('');
    setFieldErrors({});
    const questions = usable.map((item) => ({ text: item.text.trim(), hint: (item.hint || '').trim() }));
    try {
      if (destination === 'new') {
        const test = await aiCreateTest({
          title: draft.title,
          description: draft.description,
          level: draft.level,
          answer_seconds: draft.answer_seconds,
          questions,
        });
        setSaved({ id: test.id, title: test.title, added: questions.length, created: true });
      } else {
        await addQuestions(Number(targetTest), questions);
        setSaved({ id: Number(targetTest), title: target?.title, added: questions.length, created: false });
      }
      setDraft(null);
    } catch (err) {
      setFieldErrors(getFieldErrors(err));
      setError(getErrorMessage(err, 'The test could not be saved.'));
    } finally {
      setBusy('');
    }
  };

  return (
    <>
      <PageHeader
        back={{ to: '/admin/tests', label: 'Mock tests' }}
        overline="Mock tests"
        title="AI generator"
        subtitle="Describe a topic and the AI writes a speaking test for you to check. Nothing is saved until you choose."
      />

      {saved && (
        <Alert tone="success" title={saved.created ? `"${saved.title}" was created as a draft` : `Questions added to "${saved.title}"`}>
          {pluralize(saved.added, 'question')} saved. Check them on the Questions page, then publish the test when it's ready.
          <div className="vmt-row vmt-row-tight" style={{ marginTop: 8 }}>
            <Button size="sm" icon={ListChecks} to={`/admin/tests/${saved.id}/questions`}>
              Open the questions
            </Button>
          </div>
        </Alert>
      )}

      <form className="vmt-card vmt-stack vmt-stack-lg vmt-gen-step" onSubmit={writeTest} noValidate aria-labelledby="gen-step-1">
        <h2 id="gen-step-1" className="title-sm">
          <span className="vmt-gen-num" aria-hidden="true">1</span> What should the test be about?
        </h2>
        <div className="vmt-stack vmt-stack-sm">
          <TextField
            as="textarea"
            rows={2}
            label="Topic"
            value={settings.topic}
            onChange={set('topic')}
            error={fieldErrors.topic}
            placeholder="Job interview for hotel receptionists"
            help="A few words are enough. Add who it's for or what to practise if you like."
          />
          <div className="vmt-topic-chips" aria-label="Topic ideas">
            {TOPIC_IDEAS.map((idea) => (
              <button key={idea} type="button" className="vmt-topic-chip" onClick={() => setSettings((current) => ({ ...current, topic: idea }))}>
                {idea}
              </button>
            ))}
          </div>
        </div>
        <div className="vmt-grid-3">
          <TextField as="select" label="Level" value={settings.level} onChange={set('level')}>
            {LEVELS.map((level) => (
              <option key={level.value} value={level.value}>
                {level.label}
              </option>
            ))}
          </TextField>
          <TextField as="select" label="Number of questions" value={settings.count} onChange={set('count')}>
            {COUNTS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </TextField>
          <TextField as="select" label="Speaking time per question" value={settings.answer_seconds} onChange={set('answer_seconds')}>
            {TIMES.map((value) => (
              <option key={value} value={value}>
                {formatDuration(value)}
              </option>
            ))}
          </TextField>
        </div>
        <div className="vmt-stack vmt-stack-sm">
          <span className="label" id="style-label">
            Question style
          </span>
          <div className="vmt-topic-chips" role="radiogroup" aria-labelledby="style-label">
            {STYLES.map((style) => (
              <button
                key={style.value}
                type="button"
                role="radio"
                aria-checked={settings.style === style.value}
                className={`vmt-topic-chip${settings.style === style.value ? ' is-active' : ''}`}
                onClick={() => setSettings((current) => ({ ...current, style: style.value }))}
              >
                {style.label}
              </button>
            ))}
          </div>
        </div>
        {error && !draft && <Alert tone="danger">{error}</Alert>}
        <div>
          <Button type="submit" icon={draft ? RefreshCw : Sparkles} variant={draft ? 'secondary' : 'primary'} loading={busy === 'writing'}>
            {busy === 'writing' ? 'Writing the test…' : draft ? 'Write a new version' : 'Write the test'}
          </Button>
        </div>
      </form>

      {draft && (
        <section className="vmt-card vmt-stack vmt-stack-lg vmt-gen-step" aria-labelledby="gen-step-2">
          <h2 id="gen-step-2" className="title-sm">
            <span className="vmt-gen-num" aria-hidden="true">2</span> Check the questions
          </h2>
          {draft.is_demo && <Alert tone="info">Demo mode is on, so the questions come from the built-in question bank.</Alert>}
          {destination === 'new' && (
            <div className="vmt-stack">
              <TextField
                label="Test title"
                value={draft.title}
                onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
                error={fieldErrors.title}
              />
              <TextField
                as="textarea"
                rows={2}
                label="Description"
                value={draft.description}
                onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))}
                error={fieldErrors.description}
              />
            </div>
          )}
          <ol className="vmt-gen-list" aria-label="Questions">
            {draft.questions.map((item, index) => (
              <li key={`${index}-${item.text.slice(0, 16)}`} className="vmt-gen-question">
                <span className="vmt-step-num" aria-hidden="true">
                  {index + 1}
                </span>
                <div className="vmt-stack vmt-stack-sm" style={{ flex: 1, minWidth: 0 }}>
                  <TextField as="textarea" rows={2} label={`Question ${index + 1}`} value={item.text} onChange={editQuestion(index, 'text')} />
                  <TextField label={`Hint for question ${index + 1}`} value={item.hint || ''} onChange={editQuestion(index, 'hint')} />
                  <div className="vmt-row vmt-row-tight">
                    <Button size="sm" variant="ghost" icon={RefreshCw} loading={busy === `rewrite-${index}`} disabled={Boolean(busy)} onClick={() => oneMore(index)}>
                      Rewrite
                    </Button>
                    <Button size="sm" variant="ghost" icon={Trash2} disabled={Boolean(busy)} onClick={() => removeQuestion(index)}>
                      Remove
                    </Button>
                  </div>
                </div>
              </li>
            ))}
          </ol>
          {error && <Alert tone="danger">{error}</Alert>}
          <div>
            <Button variant="secondary" icon={Plus} loading={busy === 'adding'} disabled={Boolean(busy) || draft.questions.length >= MAX_QUESTIONS} onClick={() => oneMore()}>
              Add one more question
            </Button>
          </div>
        </section>
      )}

      {draft && (
        <section className="vmt-card vmt-stack vmt-stack-lg vmt-gen-step" aria-labelledby="gen-step-3">
          <h2 id="gen-step-3" className="title-sm">
            <span className="vmt-gen-num" aria-hidden="true">3</span> Save
          </h2>
          <div className="vmt-choice-row" role="radiogroup" aria-label="Where to save">
            <button type="button" role="radio" aria-checked={destination === 'new'} className={`vmt-choice${destination === 'new' ? ' is-active' : ''}`} onClick={() => setDestination('new')}>
              Create a new draft test
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={destination === 'existing'}
              className={`vmt-choice${destination === 'existing' ? ' is-active' : ''}`}
              onClick={() => setDestination('existing')}
              disabled={tests.length === 0}
            >
              Add to an existing test
            </button>
          </div>
          {destination === 'existing' && (
            <TextField as="select" label="Test" value={targetTest} onChange={(event) => setTargetTest(event.target.value)} error={fieldErrors.test}>
              <option value="">Choose a test</option>
              {tests.map((test) => (
                <option key={test.id} value={test.id}>
                  {test.title} ({pluralize(test.question_count, 'question')}, {test.status})
                </option>
              ))}
            </TextField>
          )}
          <p className="body-sm vmt-muted">
            {destination === 'new'
              ? `A draft test with ${pluralize(usable.length, 'question')}, ${formatDuration(draft.answer_seconds)} speaking time each. Students can't see it until you publish it.`
              : 'The questions are added at the end of the test. If the test is published, students see them in their next attempt.'}
          </p>
          <div>
            <Button
              icon={Save}
              loading={busy === 'saving'}
              disabled={usable.length === 0 || (destination === 'existing' && !targetTest) || (destination === 'new' && draft.title.trim().length < 3)}
              onClick={save}
            >
              {destination === 'new' ? 'Create draft test' : `Add ${pluralize(usable.length, 'question')}`}
            </Button>
          </div>
        </section>
      )}
    </>
  );
}
