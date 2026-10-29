import { useState } from 'react';
import { Plus, RefreshCw, Sparkles } from 'lucide-react';
import { addQuestions, generateQuestions } from '../services/adminService';
import { getErrorMessage } from '../services/api';
import Alert from './Alert';
import Button from './Button';
import TextField from './TextField';

const COUNTS = [1, 2, 3, 4, 5, 6, 8, 10];

/**
 * "Write questions with AI" on the admin Questions page: ask for suggestions, edit or untick them,
 * then add the chosen ones to the test in one go. Nothing is saved until "Add".
 */
export default function AiQuestionWriter({ test, onAdded }) {
  const [topic, setTopic] = useState(test.title);
  const [count, setCount] = useState(3);
  const [suggestions, setSuggestions] = useState(null); // [{ text, hint, chosen }]
  const [isDemo, setIsDemo] = useState(false);
  const [busy, setBusy] = useState(''); // '' | 'writing' | 'adding'
  const [error, setError] = useState('');

  const write = async () => {
    setBusy('writing');
    setError('');
    try {
      const data = await generateQuestions({ test: test.id, count: Number(count), topic: topic.trim() });
      setSuggestions(data.questions.map((item) => ({ ...item, chosen: true })));
      setIsDemo(data.is_demo);
    } catch (err) {
      setError(getErrorMessage(err, 'The AI could not write questions right now. Try again in a minute.'));
    } finally {
      setBusy('');
    }
  };

  const change = (index, field) => (event) => {
    const value = field === 'chosen' ? event.target.checked : event.target.value;
    setSuggestions((items) => items.map((item, position) => (position === index ? { ...item, [field]: value } : item)));
  };

  const chosen = (suggestions || []).filter((item) => item.chosen && item.text.trim().length >= 5);

  const add = async () => {
    setBusy('adding');
    setError('');
    try {
      const questions = await addQuestions(
        test.id,
        chosen.map((item) => ({ text: item.text.trim(), hint: item.hint.trim() })),
      );
      setSuggestions(null);
      onAdded(questions, chosen.length);
    } catch (err) {
      setError(getErrorMessage(err, 'The questions could not be added.'));
    } finally {
      setBusy('');
    }
  };

  return (
    <section className="vmt-card vmt-stack vmt-ai-writer" aria-labelledby="ai-writer-title">
      <div className="vmt-row vmt-row-tight">
        <span className="vmt-ai-writer-icon" aria-hidden="true">
          <Sparkles className="vmt-icon" />
        </span>
        <div className="vmt-stack" style={{ gap: 2 }}>
          <h2 id="ai-writer-title" className="title-sm">
            Write questions with AI
          </h2>
          <p className="body-sm vmt-muted">Get suggestions for this test, edit them, then add the ones you want.</p>
        </div>
      </div>

      <div className="vmt-ai-writer-form">
        <TextField label="Topic" value={topic} onChange={(event) => setTopic(event.target.value)} help="The test title is used if you leave it empty." />
        <TextField as="select" label="How many" value={count} onChange={(event) => setCount(event.target.value)}>
          {COUNTS.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </TextField>
        <Button icon={suggestions ? RefreshCw : Sparkles} variant={suggestions ? 'secondary' : 'primary'} loading={busy === 'writing'} onClick={write}>
          {suggestions ? 'Write different ones' : 'Write questions'}
        </Button>
      </div>

      {error && <Alert tone="danger">{error}</Alert>}
      {busy === 'writing' && <p className="body-sm vmt-muted">Writing questions for a {test.level} level test…</p>}

      {suggestions && (
        <>
          {isDemo && <Alert tone="info">Demo mode is on, so these come from the built-in question bank.</Alert>}
          <ol className="vmt-suggestions" aria-label="Suggested questions">
            {suggestions.map((item, index) => (
              <li key={`${index}-${item.text.slice(0, 20)}`} className={`vmt-suggestion${item.chosen ? '' : ' is-off'}`}>
                <label className="vmt-check vmt-suggestion-check">
                  <input type="checkbox" checked={item.chosen} onChange={change(index, 'chosen')} />
                  <span className="sr-only">Use suggestion {index + 1}</span>
                </label>
                <div className="vmt-stack vmt-stack-sm" style={{ flex: 1, minWidth: 0 }}>
                  <TextField as="textarea" rows={2} label={`Suggestion ${index + 1}`} value={item.text} onChange={change(index, 'text')} />
                  <TextField label="Hint" value={item.hint} onChange={change(index, 'hint')} />
                </div>
              </li>
            ))}
          </ol>
          <div className="vmt-row">
            <Button icon={Plus} onClick={add} loading={busy === 'adding'} disabled={chosen.length === 0}>
              {chosen.length === 1 ? 'Add 1 question' : `Add ${chosen.length} questions`}
            </Button>
            <Button variant="ghost" onClick={() => setSuggestions(null)}>
              Discard
            </Button>
          </div>
        </>
      )}
    </section>
  );
}
