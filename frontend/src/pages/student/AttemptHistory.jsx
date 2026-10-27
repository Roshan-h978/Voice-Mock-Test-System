import { useEffect, useState } from 'react';
import { History } from 'lucide-react';
import Alert from '../../components/Alert';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import LoadingSpinner from '../../components/LoadingSpinner';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import { getErrorMessage } from '../../services/api';
import { getMyAttempts } from '../../services/resultService';
import { PAGE_SIZE } from '../../utils/constants';
import { formatDate, formatScore, levelLabel } from '../../utils/formatters';

const FILTERS = [
  { value: 'finished', label: 'Finished' },
  { value: 'in_progress', label: 'In progress' },
  { value: '', label: 'All' },
];

export default function AttemptHistory() {
  const [filter, setFilter] = useState('finished');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setData(null);
    setError('');
    getMyAttempts({ status: filter || undefined, page, page_size: PAGE_SIZE })
      .then((response) => active && setData(response))
      .catch((err) => active && setError(getErrorMessage(err)));
    return () => {
      active = false;
    };
  }, [filter, page]);

  const changeFilter = (value) => {
    setFilter(value);
    setPage(1);
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;

  return (
    <>
      <PageHeader overline="History" title="My results" subtitle="Every test you have taken, newest first." />

      <div className="vmt-tabs" role="tablist" aria-label="Filter results">
        {FILTERS.map((item) => (
          <button
            key={item.label}
            type="button"
            role="tab"
            aria-selected={filter === item.value}
            className={`vmt-tab${filter === item.value ? ' is-active' : ''}`}
            onClick={() => changeFilter(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {error && <Alert tone="danger">{error}</Alert>}
      {!data && !error && <LoadingSpinner label="Loading your results…" />}

      {data && data.results.length === 0 && (
        <div className="vmt-card">
          <EmptyState icon={History} title="Nothing here yet" action={<Button to="/student">Choose a test</Button>}>
            Your test results will appear here after you finish a test.
          </EmptyState>
        </div>
      )}

      {data && data.results.length > 0 && (
        <>
          <div className="vmt-table-wrap">
            <table className="vmt-table">
              <thead>
                <tr>
                  <th scope="col">Test</th>
                  <th scope="col">Date</th>
                  <th scope="col" className="is-num">Fluency</th>
                  <th scope="col" className="is-num">Pronunciation</th>
                  <th scope="col" className="is-num">Grammar</th>
                  <th scope="col" className="is-num">Overall</th>
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
                      <span className="vmt-cell-main">{attempt.test.title}</span>
                      <br />
                      <span className="caption vmt-muted">{levelLabel(attempt.test.level)}</span>
                    </td>
                    <td>{formatDate(attempt.submitted_at || attempt.started_at)}</td>
                    <td className="is-num">{formatScore(attempt.fluency)}</td>
                    <td className="is-num">{formatScore(attempt.pronunciation)}</td>
                    <td className="is-num">{formatScore(attempt.grammar)}</td>
                    <td className="is-num vmt-cell-main">{formatScore(attempt.overall)}</td>
                    <td>
                      <StatusBadge kind="attempt" status={attempt.status} />
                    </td>
                    <td className="is-actions">
                      {attempt.status === 'in_progress' ? (
                        <Button size="sm" to={`/student/attempts/${attempt.id}`}>
                          Continue
                        </Button>
                      ) : (
                        <Button size="sm" variant="secondary" to={`/student/results/${attempt.id}`}>
                          View
                        </Button>
                      )}
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
    </>
  );
}
