import { useEffect, useMemo, useState } from 'react';
import { ArrowDownRight, ArrowRight, ArrowUpRight, Flame, Mic, Target } from 'lucide-react';
import { Link } from 'react-router-dom';
import Alert from '../../components/Alert';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import LoadingSpinner from '../../components/LoadingSpinner';
import PageHeader from '../../components/PageHeader';
import ScoreChart from '../../components/ScoreChart';
import SkillBar from '../../components/SkillBar';
import { getErrorMessage } from '../../services/api';
import { getProgress } from '../../services/learningService';
import { SKILLS } from '../../utils/constants';
import { formatDate, formatScore, pluralize, skillLabel } from '../../utils/formatters';

const RANGES = [
  { value: 30, label: '30 days' },
  { value: 90, label: '90 days' },
  { value: 365, label: '12 months' },
  { value: 0, label: 'All time' },
];
const CHART_SKILLS = [{ key: 'overall', label: 'Overall' }, ...SKILLS];
const HEAT_LEVELS = ['#eef2f6', '#bfe8e3', '#6fcbc2', '#2aa79c', '#00756b']; // one hue, light to dark
const WEEKDAYS = ['Mon', '', 'Wed', '', 'Fri', '', ''];

function Change({ value }) {
  if (value === null || value === undefined) return <span className="caption vmt-muted">Not enough results to compare yet</span>;
  if (value === 0) return <span className="caption vmt-muted">No change since your earlier results</span>;
  const Icon = value > 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={`vmt-change ${value > 0 ? 'is-up' : 'is-down'}`}>
      <Icon className="vmt-icon-sm" aria-hidden="true" />
      {value > 0 ? '+' : ''}
      {value} since your earlier results
    </span>
  );
}

/** 12 weeks of practice days, Monday to Sunday, darker = more answers that day. */
function ActivityCalendar({ activity }) {
  const columns = useMemo(() => {
    if (!activity.length) return [];
    const firstDay = new Date(`${activity[0].date}T00:00:00`);
    const leading = (firstDay.getDay() + 6) % 7; // Monday = 0
    const cells = [...Array(leading).fill(null), ...activity];
    const weeks = [];
    for (let index = 0; index < cells.length; index += 7) weeks.push(cells.slice(index, index + 7));
    return weeks;
  }, [activity]);
  const activeDays = activity.filter((day) => day.count > 0).length;

  return (
    <div className="vmt-heat-wrap">
      <div className="vmt-heat" role="img" aria-label={`Practice calendar: active on ${pluralize(activeDays, 'day')} in the last 12 weeks.`}>
        <div className="vmt-heat-days" aria-hidden="true">
          {WEEKDAYS.map((day, index) => (
            <span key={index}>{day}</span>
          ))}
        </div>
        {columns.map((week, weekIndex) => (
          <div key={weekIndex} className="vmt-heat-week" aria-hidden="true">
            {week.map((day, dayIndex) =>
              day ? (
                <span
                  key={day.date}
                  className="vmt-heat-cell"
                  style={{ background: HEAT_LEVELS[Math.min(day.count, 4)] }}
                  title={`${formatDate(day.date)}: ${day.count ? pluralize(day.count, 'answer') : 'no practice'}`}
                />
              ) : (
                <span key={`empty-${dayIndex}`} className="vmt-heat-cell is-blank" />
              ),
            )}
          </div>
        ))}
      </div>
      <div className="vmt-heat-legend" aria-hidden="true">
        <span>Less</span>
        {HEAT_LEVELS.map((color) => (
          <span key={color} className="vmt-heat-cell" style={{ background: color }} />
        ))}
        <span>More</span>
      </div>
    </div>
  );
}

/** Scores over time, skill trends, the weakest skill, practice calendar and best score per test. */
export default function MyProgress() {
  const [days, setDays] = useState(90);
  const [chartSkill, setChartSkill] = useState('overall');
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setError('');
    getProgress(days)
      .then((response) => active && setData(response))
      .catch((err) => active && setError(getErrorMessage(err, 'Your progress could not be loaded.')));
    return () => {
      active = false;
    };
  }, [days]);

  const nothingYet = data && data.totals.tests_completed === 0 && data.totals.practice_answers === 0;
  const inRange = data ? data.timeline.length + data.practice.length : 0;
  const chartLabel = CHART_SKILLS.find((item) => item.key === chartSkill)?.label;

  return (
    <>
      <PageHeader overline="Progress" title="My progress" subtitle="How your speaking scores change over time, and what to work on next." />

      <div className="vmt-tabs" role="tablist" aria-label="Time range">
        {RANGES.map((range) => (
          <button
            key={range.value}
            type="button"
            role="tab"
            aria-selected={days === range.value}
            className={`vmt-tab${days === range.value ? ' is-active' : ''}`}
            onClick={() => setDays(range.value)}
          >
            {range.label}
          </button>
        ))}
      </div>

      {error && <Alert tone="danger">{error}</Alert>}
      {!data && !error && <LoadingSpinner label="Loading your progress…" />}

      {nothingYet && (
        <div className="vmt-card">
          <EmptyState
            icon={Target}
            title="No results yet"
            action={
              <div className="vmt-row" style={{ justifyContent: 'center' }}>
                <Button to="/student" variant="secondary">
                  Take a test
                </Button>
                <Button to="/student/practice" icon={Mic}>
                  Quick practice
                </Button>
              </div>
            }
          >
            Take a test or practise a question, and your progress shows up here.
          </EmptyState>
        </div>
      )}

      {data && !nothingYet && (
        <div className={`vmt-stack vmt-stack-lg${days !== data.days ? ' is-refreshing' : ''}`}>
          <div className="vmt-grid">
            <div className="vmt-card vmt-stat">
              <span className="vmt-stat-label">Tests completed</span>
              <span className="vmt-stat-value">{data.totals.tests_completed}</span>
              <span className="vmt-stat-sub">Average {formatScore(data.totals.average_score)}</span>
            </div>
            <div className="vmt-card vmt-stat">
              <span className="vmt-stat-label">Practice answers</span>
              <span className="vmt-stat-value">{data.totals.practice_answers}</span>
            </div>
            <div className="vmt-card vmt-stat">
              <span className="vmt-stat-label">Minutes spoken</span>
              <span className="vmt-stat-value">{data.totals.minutes_spoken}</span>
            </div>
            <div className="vmt-card vmt-stat">
              <div className="vmt-stat-top">
                <span className="vmt-stat-label">Day streak</span>
                <span className="vmt-stat-icon vmt-streak-icon" aria-hidden="true">
                  <Flame className="vmt-icon" />
                </span>
              </div>
              <span className="vmt-stat-value">{pluralize(data.streak.current, 'day')}</span>
              <span className="vmt-stat-sub">Longest {pluralize(data.streak.longest, 'day')}</span>
            </div>
          </div>

          <section className="vmt-card vmt-stack" aria-labelledby="chart-title">
            <div className="vmt-card-head" style={{ marginBottom: 0 }}>
              <h2 id="chart-title" className="title-sm">
                Scores over time
              </h2>
              <div className="vmt-tabs vmt-tabs-sm" role="tablist" aria-label="Score">
                {CHART_SKILLS.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    role="tab"
                    aria-selected={chartSkill === item.key}
                    className={`vmt-tab${chartSkill === item.key ? ' is-active' : ''}`}
                    onClick={() => setChartSkill(item.key)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
            {inRange === 0 ? (
              <p className="body-sm vmt-muted">No results in this time range. Choose a longer range above.</p>
            ) : (
              <>
                <ScoreChart tests={data.timeline} practice={data.practice} skill={chartSkill} skillLabel={chartLabel} />
                <details className="vmt-chart-table">
                  <summary className="body-sm">Show the numbers</summary>
                  <div className="vmt-table-wrap">
                    <table className="vmt-table" style={{ minWidth: 520 }}>
                      <thead>
                        <tr>
                          <th scope="col">Date</th>
                          <th scope="col">What</th>
                          {CHART_SKILLS.map((item) => (
                            <th key={item.key} scope="col" className="is-num">
                              {item.label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {[...data.timeline, ...data.practice]
                          .sort((a, b) => new Date(b.date) - new Date(a.date))
                          .map((row) => (
                            <tr key={`${row.kind}-${row.id}`}>
                              <td>{formatDate(row.date)}</td>
                              <td>
                                <Link to={row.kind === 'test' ? `/student/results/${row.id}` : `/student/practice/${row.id}`} className="vmt-link">
                                  {row.title}
                                </Link>
                              </td>
                              {CHART_SKILLS.map((item) => (
                                <td key={item.key} className="is-num">
                                  {formatScore(row[item.key])}
                                </td>
                              ))}
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              </>
            )}
          </section>

          <div className="vmt-split vmt-split-even">
            <section className="vmt-card vmt-stack" aria-labelledby="skills-title">
              <h2 id="skills-title" className="title-sm">
                Your skills now
              </h2>
              <p className="caption vmt-muted">Average of your latest 5 results (tests and practice).</p>
              {SKILLS.map((skill) => (
                <div key={skill.key} className={`vmt-skill-trend${data.focus_skill === skill.key ? ' is-focus' : ''}`}>
                  <SkillBar label={skill.label} value={data.skills[skill.key].current} />
                  <Change value={data.skills[skill.key].change} />
                </div>
              ))}
              {data.focus_skill && (
                <div className="vmt-callout vmt-callout-warning">
                  <span className="overline">Work on {skillLabel(data.focus_skill).toLowerCase()} next</span>
                  <span className="body-sm">{data.focus_advice}</span>
                  <div>
                    <Button size="sm" iconRight={ArrowRight} to="/student/practice">
                      Practise now
                    </Button>
                  </div>
                </div>
              )}
            </section>

            <section className="vmt-card vmt-stack" aria-labelledby="calendar-title">
              <h2 id="calendar-title" className="title-sm">
                Practice calendar
              </h2>
              <p className="caption vmt-muted">
                Active on {pluralize(data.totals.active_days_30, 'day')} in the last 30 days. A short answer every day builds the habit.
              </p>
              <ActivityCalendar activity={data.activity} />
            </section>
          </div>

          {data.best_by_test.length > 0 && (
            <section className="vmt-stack" aria-labelledby="best-title">
              <h2 id="best-title" className="title-md">
                Best score per test
              </h2>
              <div className="vmt-table-wrap">
                <table className="vmt-table" style={{ minWidth: 520 }}>
                  <thead>
                    <tr>
                      <th scope="col">Test</th>
                      <th scope="col" className="is-num">
                        Times taken
                      </th>
                      <th scope="col" className="is-num">
                        Best
                      </th>
                      <th scope="col">Last taken</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.best_by_test.map((row) => (
                      <tr key={row.test_id}>
                        <td className="vmt-cell-main">{row.title}</td>
                        <td className="is-num">{row.attempts}</td>
                        <td className="is-num vmt-cell-main">{formatScore(row.best)}</td>
                        <td>{formatDate(row.last_taken)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      )}
    </>
  );
}
