import { useCallback, useEffect, useState } from 'react';
import { BookOpenCheck, Check, Lightbulb, Mic, Undo2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import Alert from '../../components/Alert';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import LoadingSpinner from '../../components/LoadingSpinner';
import PageHeader from '../../components/PageHeader';
import { getErrorMessage } from '../../services/api';
import { getNotebook, setLearned } from '../../services/learningService';
import { pluralize, timeAgo } from '../../utils/formatters';

const TABS = [
  { value: 'to_learn', label: 'To learn' },
  { value: 'learned', label: 'Learned' },
  { value: 'all', label: 'All' },
];

function Sources({ item }) {
  return (
    <span className="caption vmt-muted">
      {item.count > 1 ? `${item.count} times, last ${timeAgo(item.last_seen)}. ` : `${timeAgo(item.last_seen)}. `}
      From{' '}
      {item.sources.map((source, index) => (
        <span key={`${source.link}-${index}`}>
          {index > 0 && ', '}
          <Link to={source.link} className="vmt-link" title={source.question}>
            {source.title}
          </Link>
        </span>
      ))}
    </span>
  );
}

function LearnedButton({ item, onToggle, busy }) {
  return (
    <Button
      size="sm"
      variant={item.learned ? 'ghost' : 'secondary'}
      icon={item.learned ? Undo2 : Check}
      loading={busy}
      onClick={() => onToggle(item)}
      aria-label={item.learned ? 'Move back to To learn' : "I've learned this"}
    >
      {item.learned ? 'Not learned yet' : "I've learned this"}
    </Button>
  );
}

/** Every correction and tip from the student's tests and practice, grouped, with "learned" ticks. */
export default function Notebook() {
  const [show, setShow] = useState('to_learn');
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busyKey, setBusyKey] = useState('');
  const [undo, setUndo] = useState(null);

  const load = useCallback(async () => {
    setError('');
    try {
      setData(await getNotebook(show));
    } catch (err) {
      setError(getErrorMessage(err, 'Your notebook could not be loaded.'));
    }
  }, [show]);

  useEffect(() => {
    setData(null);
    load();
  }, [load]);

  const toggle = async (item) => {
    setBusyKey(item.key);
    try {
      await setLearned(item.key, !item.learned);
      setUndo(item.learned ? null : item);
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyKey('');
    }
  };

  const undoLast = async () => {
    const item = undo;
    setUndo(null);
    await setLearned(item.key, false).catch(() => {});
    load();
  };

  const empty = data && data.corrections.length === 0 && data.tips.length === 0;

  return (
    <>
      <PageHeader
        overline="Learning"
        title="Mistakes notebook"
        subtitle="Every correction and tip from your tests and practice in one place. Tick the ones you've learned."
      />

      {data && (
        <div className="vmt-grid">
          <div className="vmt-card vmt-stat">
            <span className="vmt-stat-label">Corrections</span>
            <span className="vmt-stat-value">{data.totals.corrections}</span>
          </div>
          <div className="vmt-card vmt-stat">
            <span className="vmt-stat-label">Tips</span>
            <span className="vmt-stat-value">{data.totals.tips}</span>
          </div>
          <div className="vmt-card vmt-stat">
            <span className="vmt-stat-label">Learned</span>
            <span className="vmt-stat-value">{data.totals.learned}</span>
          </div>
        </div>
      )}

      <div className="vmt-tabs" role="tablist" aria-label="Show">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={show === tab.value}
            className={`vmt-tab${show === tab.value ? ' is-active' : ''}`}
            onClick={() => {
              setShow(tab.value);
              setUndo(null);
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {undo && (
        <Alert tone="success" onClose={() => setUndo(null)}>
          Moved to Learned.{' '}
          <button type="button" className="vmt-link vmt-link-button" onClick={undoLast}>
            Undo
          </button>
        </Alert>
      )}
      {error && <Alert tone="danger">{error}</Alert>}
      {!data && !error && <LoadingSpinner label="Opening your notebook…" />}

      {empty && (
        <div className="vmt-card">
          <EmptyState
            icon={BookOpenCheck}
            title={show === 'learned' ? 'Nothing ticked yet' : data.totals.corrections + data.totals.tips ? 'All learned. Well done!' : 'Your notebook is empty'}
            action={
              show !== 'learned' && (
                <Button to="/student/practice" icon={Mic}>
                  Practise a question
                </Button>
              )
            }
          >
            {show === 'learned'
              ? 'When you learn a correction or tip, tick it and it moves here.'
              : 'Corrections and tips from your tests and Quick practice appear here.'}
          </EmptyState>
        </div>
      )}

      {data && data.corrections.length > 0 && (
        <section className="vmt-stack" aria-labelledby="corrections-title">
          <h2 id="corrections-title" className="title-md">
            Corrections <span className="body-sm vmt-muted">({data.corrections.length})</span>
          </h2>
          <ul className="vmt-notebook-list">
            {data.corrections.map((item) => (
              <li key={item.key} className={`vmt-card vmt-notebook-item${item.learned ? ' is-learned' : ''}`}>
                <div className="vmt-notebook-pair">
                  <div className="vmt-notebook-said">
                    <span className="caption">You said</span>
                    <span className="body">“{item.said}”</span>
                  </div>
                  <div className="vmt-notebook-better">
                    <span className="caption">Better</span>
                    <span className="body">“{item.better}”</span>
                  </div>
                </div>
                <div className="vmt-notebook-foot">
                  <Sources item={item} />
                  <LearnedButton item={item} onToggle={toggle} busy={busyKey === item.key} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {data && data.tips.length > 0 && (
        <section className="vmt-stack" aria-labelledby="tips-title">
          <h2 id="tips-title" className="title-md">
            Tips <span className="body-sm vmt-muted">({data.tips.length})</span>
          </h2>
          <ul className="vmt-notebook-list">
            {data.tips.map((item) => (
              <li key={item.key} className={`vmt-card vmt-notebook-item vmt-notebook-tip${item.learned ? ' is-learned' : ''}`}>
                <div className="vmt-row vmt-row-tight" style={{ alignItems: 'flex-start', flexWrap: 'nowrap' }}>
                  <span className="vmt-check-icon is-tip" aria-hidden="true">
                    <Lightbulb className="vmt-icon-sm" />
                  </span>
                  <span className="body">{item.text}</span>
                </div>
                <div className="vmt-notebook-foot">
                  <Sources item={item} />
                  <LearnedButton item={item} onToggle={toggle} busy={busyKey === item.key} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {data && !empty && (
        <p className="body-sm vmt-muted">
          {pluralize(data.totals.corrections + data.totals.tips - data.totals.learned, 'item')} left to learn. Practising a
          question again is the quickest way to fix a mistake.
        </p>
      )}
    </>
  );
}
