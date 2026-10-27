import { useCallback, useEffect, useState } from 'react';
import { Award, ClipboardList, Mic, PlayCircle, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';
import Alert from '../../components/Alert';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import LoadingSpinner from '../../components/LoadingSpinner';
import PageHeader from '../../components/PageHeader';
import SkillBar from '../../components/SkillBar';
import StatCard from '../../components/StatCard';
import StatusBadge from '../../components/StatusBadge';
import { useAuth } from '../../context/AuthContext';
import { getErrorMessage } from '../../services/api';
import { getMyAttempts, getMyStats } from '../../services/resultService';
import { getTests } from '../../services/testService';
import { SKILLS } from '../../utils/constants';
import { firstName, formatDate, formatScore, levelLabel, pluralize, skillLabel } from '../../utils/formatters';

export default function StudentDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState({ stats: null, tests: [], unfinished: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [stats, tests, inProgress] = await Promise.all([
        getMyStats(),
        getTests(),
        getMyAttempts({ status: 'in_progress', page_size: 1 }),
      ]);
      setData({ stats, tests, unfinished: inProgress.results[0] || null });
    } catch (err) {
      setError(getErrorMessage(err, 'We could not load your dashboard.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const { stats, tests, unfinished } = data;

  return (
    <>
      <PageHeader
        overline="Dashboard"
        title={`Hi, ${firstName(user?.full_name)}`}
        subtitle="Ready for some speaking practice? Choose a test below."
      />

      {loading && <LoadingSpinner label="Loading your dashboard…" />}
      {!loading && error && (
        <Alert tone="danger" title="Something went wrong">
          {error}{' '}
          <button type="button" className="vmt-link" style={{ border: 0, background: 'none', padding: 0, cursor: 'pointer' }} onClick={load}>
            Try again
          </button>
        </Alert>
      )}

      {!loading && !error && stats && (
        <>
          {unfinished && (
            <div className="vmt-banner">
              <div className="vmt-stack vmt-stack-sm">
                <span className="title-sm">You have an unfinished test: {unfinished.test.title}</span>
                <span className="body-sm vmt-muted">Your saved answers are kept. Pick up where you left off.</span>
              </div>
              <Button to={`/student/attempts/${unfinished.id}`} icon={PlayCircle}>
                Continue test
              </Button>
            </div>
          )}

          <div className="vmt-grid">
            <StatCard label="Tests completed" value={stats.completed_tests} icon={ClipboardList} />
            <StatCard
              label="Average score"
              value={formatScore(stats.average_score)}
              sub={stats.best_score !== null ? `Best: ${formatScore(stats.best_score)}` : 'Take a test to see your score'}
              icon={Award}
            />
            <StatCard
              label="Strongest skill"
              value={stats.strongest_skill ? skillLabel(stats.strongest_skill) : '—'}
              sub={stats.focus_skill ? `Focus on: ${skillLabel(stats.focus_skill)}` : ''}
              icon={TrendingUp}
            />
          </div>

          <div className="vmt-split">
            <section className="vmt-stack" aria-labelledby="tests-title">
              <div className="vmt-row vmt-row-between">
                <h2 id="tests-title" className="title-md">
                  Mock tests
                </h2>
                <span className="body-sm vmt-muted">{pluralize(tests.length, 'test')}</span>
              </div>
              {tests.length === 0 ? (
                <div className="vmt-card">
                  <EmptyState icon={ClipboardList} title="No tests yet">
                    Your teacher hasn't published any tests yet. Please check back soon.
                  </EmptyState>
                </div>
              ) : (
                tests.map((test) => {
                  const taken = test.my_attempt_count > 0;
                  return (
                    <div key={test.id} className="vmt-test">
                      <span className="vmt-test-icon" aria-hidden="true">
                        <Mic className="vmt-icon-lg" />
                      </span>
                      <div className="vmt-test-body">
                        <span className="title-sm">{test.title}</span>
                        <span className="vmt-meta">
                          {levelLabel(test.level)} · {pluralize(test.question_count, 'question')} · about {test.estimated_minutes} min
                          {taken && test.my_best_score !== null ? ` · Best ${formatScore(test.my_best_score)}` : ''}
                        </span>
                      </div>
                      <StatusBadge tone={taken ? 'ready' : 'locked'}>{taken ? `Taken ${test.my_attempt_count}×` : 'New'}</StatusBadge>
                      <Button to={`/student/tests/${test.id}`} variant={taken ? 'secondary' : 'primary'}>
                        {!taken ? 'Start' : test.allow_retake ? 'Take again' : 'View'}
                      </Button>
                    </div>
                  );
                })
              )}
            </section>

            <aside className="vmt-stack vmt-stack-lg">
              <div className="vmt-card vmt-stack">
                <h2 className="title-sm">Your skills</h2>
                {stats.completed_tests === 0 ? (
                  <p className="body-sm vmt-muted">Finish your first test to see your skill scores here.</p>
                ) : (
                  SKILLS.map((skill) => (
                    <SkillBar key={skill.key} label={skill.label} value={stats.skills[skill.key]} description={skill.description} />
                  ))
                )}
              </div>

              <div className="vmt-card vmt-stack">
                <div className="vmt-row vmt-row-between">
                  <h2 className="title-sm">Recent results</h2>
                  <Link to="/student/history" className="vmt-link body-sm">
                    See all
                  </Link>
                </div>
                {stats.recent.length === 0 ? (
                  <p className="body-sm vmt-muted">Your results will appear here.</p>
                ) : (
                  stats.recent.map((item) => (
                    <Link key={item.id} to={`/student/results/${item.id}`} className="vmt-row vmt-row-between" style={{ textDecoration: 'none' }}>
                      <span className="vmt-stack" style={{ gap: 0 }}>
                        <span className="label">{item.test_title}</span>
                        <span className="caption vmt-muted">{formatDate(item.submitted_at)}</span>
                      </span>
                      <span className="title-sm vmt-num">{formatScore(item.overall)}</span>
                    </Link>
                  ))
                )}
              </div>
            </aside>
          </div>
        </>
      )}
    </>
  );
}
