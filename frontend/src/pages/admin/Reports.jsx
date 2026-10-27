import { useEffect, useMemo, useState } from 'react';
import { Award, ChartColumn, ClipboardList, Download, MessageSquare, Users } from 'lucide-react';
import Alert from '../../components/Alert';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import LoadingSpinner from '../../components/LoadingSpinner';
import PageHeader from '../../components/PageHeader';
import SkillBar from '../../components/SkillBar';
import StatCard from '../../components/StatCard';
import TextField from '../../components/TextField';
import { downloadReportCsv, getReport, getTests } from '../../services/adminService';
import { getErrorMessage } from '../../services/api';
import { LEVELS, SKILLS } from '../../utils/constants';
import { formatDate, formatScore, levelLabel, pluralize, toInputDate } from '../../utils/formatters';

const DAY_MS = 24 * 60 * 60 * 1000;

function defaultFilters() {
  const today = new Date();
  return {
    date_from: toInputDate(new Date(today.getFullYear(), today.getMonth(), today.getDate() - 29)),
    date_to: toInputDate(today),
    test: '',
    level: '',
  };
}

/** Every day in the range, with 0 for days without tests (up to ~2 months; longer ranges show active days only). */
function dailySeries(daily, from, to) {
  const byDay = Object.fromEntries(daily.map((row) => [row.date, row]));
  const start = new Date(`${from}T00:00:00`);
  const end = new Date(`${to}T00:00:00`);
  const days = Math.round((end - start) / DAY_MS) + 1;
  if (days > 62 || days < 1) return daily;
  return Array.from({ length: days }, (_, index) => {
    // Count calendar days (not 24-hour steps), so clock changes don't repeat or skip a day.
    const date = toInputDate(new Date(start.getFullYear(), start.getMonth(), start.getDate() + index));
    return byDay[date] || { date, attempts: 0, average_score: null };
  });
}

function DailyChart({ rows }) {
  const peak = Math.max(...rows.map((row) => row.attempts), 0);
  const peakIndex = rows.findIndex((row) => row.attempts === peak);
  if (!rows.length || peak === 0) return <p className="body-sm vmt-muted">No tests were taken in this period.</p>;

  return (
    <div className="vmt-stack vmt-stack-sm">
      <div className="vmt-columns" role="img" aria-label={`Tests taken per day. Highest: ${peak} on ${formatDate(rows[peakIndex].date)}.`}>
        <span className="vmt-columns-peak" style={{ left: `${((peakIndex + 0.5) / rows.length) * 100}%` }}>
          {peak}
        </span>
        {rows.map((row) => {
          const label = `${formatDate(row.date)}: ${pluralize(row.attempts, 'test')}${row.average_score !== null ? `, average ${row.average_score}%` : ''}`;
          return (
            <span key={row.date} className="vmt-column" title={label}>
              <span className={`vmt-column-fill${row.attempts ? '' : ' is-zero'}`} style={{ height: `${(row.attempts / peak) * 100}%` }} />
            </span>
          );
        })}
      </div>
      <div className="vmt-columns-axis" aria-hidden="true">
        <span>{formatDate(rows[0].date)}</span>
        <span>{formatDate(rows[rows.length - 1].date)}</span>
      </div>
      <details>
        <summary className="vmt-link body-sm" style={{ cursor: 'pointer' }}>
          Show as a table
        </summary>
        <div className="vmt-table-wrap" style={{ marginTop: 'var(--space-1)' }}>
          <table className="vmt-table" style={{ minWidth: 0 }}>
            <thead>
              <tr>
                <th scope="col">Day</th>
                <th scope="col" className="is-num">Tests</th>
                <th scope="col" className="is-num">Average</th>
              </tr>
            </thead>
            <tbody>
              {rows
                .filter((row) => row.attempts > 0)
                .map((row) => (
                  <tr key={row.date}>
                    <td>{formatDate(row.date)}</td>
                    <td className="is-num">{row.attempts}</td>
                    <td className="is-num">{formatScore(row.average_score)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

export default function Reports() {
  const [filters, setFilters] = useState(defaultFilters);
  const [tests, setTests] = useState([]);
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    getTests()
      .then(setTests)
      .catch(() => setTests([]));
  }, []);

  useEffect(() => {
    let active = true;
    setReport(null);
    setError('');
    const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
    getReport(params)
      .then((data) => active && setReport(data))
      .catch((err) => active && setError(getErrorMessage(err, 'The report could not be loaded.')));
    return () => {
      active = false;
    };
  }, [filters]);

  const daily = useMemo(
    () => (report ? dailySeries(report.daily, report.date_from, report.date_to) : []),
    [report],
  );

  const update = (field) => (event) => setFilters((current) => ({ ...current, [field]: event.target.value }));

  const handleDownload = async () => {
    setDownloading(true);
    setError('');
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
      await downloadReportCsv(params);
    } catch (err) {
      setError(getErrorMessage(err, 'The CSV file could not be downloaded.'));
    } finally {
      setDownloading(false);
    }
  };

  const total = report?.totals.attempts || 0;
  const bands = report
    ? [
        { label: '80% +', value: report.score_bands['80_and_above'] },
        { label: '60–79%', value: report.score_bands['60_to_79'] },
        { label: 'Under 60%', value: report.score_bands.under_60 },
      ]
    : [];

  return (
    <>
      <PageHeader
        overline="Insights"
        title="Reports"
        subtitle="Scores and activity for any period. Download the results as a CSV file for Excel."
        actions={
          <Button variant="secondary" icon={Download} loading={downloading} onClick={handleDownload} disabled={!total}>
            Download CSV
          </Button>
        }
      />

      <div className="vmt-card vmt-toolbar">
        <TextField label="From" type="date" value={filters.date_from} max={filters.date_to} onChange={update('date_from')} />
        <TextField label="To" type="date" value={filters.date_to} min={filters.date_from} onChange={update('date_to')} />
        <TextField as="select" label="Test" value={filters.test} onChange={update('test')}>
          <option value="">All tests</option>
          {tests.map((test) => (
            <option key={test.id} value={test.id}>
              {test.title}
            </option>
          ))}
        </TextField>
        <TextField as="select" label="Student level" value={filters.level} onChange={update('level')}>
          <option value="">All levels</option>
          {LEVELS.map((level) => (
            <option key={level.value} value={level.value}>
              {level.label}
            </option>
          ))}
        </TextField>
      </div>

      {error && <Alert tone="danger">{error}</Alert>}
      {!report && !error && <LoadingSpinner label="Building the report…" />}

      {report && total === 0 && (
        <div className="vmt-card">
          <EmptyState icon={ChartColumn} title="No results in this period">
            Try a longer date range or another filter.
          </EmptyState>
        </div>
      )}

      {report && total > 0 && (
        <>
          <div className="vmt-grid">
            <StatCard label="Tests taken" value={total} icon={ClipboardList} />
            <StatCard label="Students" value={report.totals.students} icon={Users} />
            <StatCard label="Average score" value={formatScore(report.totals.average_score)} icon={Award} />
            <StatCard
              label="Waiting for review"
              value={report.totals.needs_review}
              sub={`${report.totals.reviewed} reviewed`}
              icon={MessageSquare}
            />
          </div>

          <div className="vmt-grid-wide">
            <div className="vmt-card vmt-stack">
              <h2 className="title-sm">Average skill scores</h2>
              {SKILLS.map((skill) => (
                <SkillBar key={skill.key} label={skill.label} value={report.skills[skill.key]} />
              ))}
            </div>
            <div className="vmt-card vmt-stack">
              <h2 className="title-sm">Score ranges</h2>
              <div className="vmt-hbars">
                {bands.map((band) => (
                  <div key={band.label} className="vmt-hbar" title={`${band.label}: ${pluralize(band.value, 'test')}`}>
                    <span className="vmt-hbar-label">{band.label}</span>
                    <div className="vmt-bar">
                      <div className="vmt-bar-fill" style={{ width: `${(band.value / total) * 100}%` }} />
                    </div>
                    <span className="vmt-hbar-value">{band.value}</span>
                  </div>
                ))}
              </div>
              <p className="caption vmt-muted">Number of finished tests in each score range.</p>
            </div>
          </div>

          <div className="vmt-card vmt-stack">
            <div className="vmt-row vmt-row-between">
              <h2 className="title-sm">Tests taken per day</h2>
              <span className="caption vmt-muted">
                {formatDate(report.date_from)} – {formatDate(report.date_to)}
              </span>
            </div>
            <DailyChart rows={daily} />
          </div>

          <section className="vmt-stack" aria-labelledby="by-test-title">
            <h2 id="by-test-title" className="title-md">
              By test
            </h2>
            <div className="vmt-table-wrap">
              <table className="vmt-table">
                <thead>
                  <tr>
                    <th scope="col">Test</th>
                    <th scope="col">Level</th>
                    <th scope="col" className="is-num">Taken</th>
                    <th scope="col" className="is-num">Students</th>
                    <th scope="col" className="is-num">Average</th>
                    <th scope="col" className="is-num">Best</th>
                    <th scope="col" className="is-num">Lowest</th>
                  </tr>
                </thead>
                <tbody>
                  {report.by_test.map((row) => (
                    <tr key={row.test_id}>
                      <td className="vmt-cell-main">{row.title}</td>
                      <td>{levelLabel(row.level)}</td>
                      <td className="is-num">{row.attempts}</td>
                      <td className="is-num">{row.students}</td>
                      <td className="is-num">{formatScore(row.average_score)}</td>
                      <td className="is-num">{formatScore(row.best_score)}</td>
                      <td className="is-num">{formatScore(row.lowest_score)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="vmt-stack" aria-labelledby="by-level-title">
            <h2 id="by-level-title" className="title-md">
              By student level
            </h2>
            <div className="vmt-table-wrap">
              <table className="vmt-table" style={{ minWidth: 0 }}>
                <thead>
                  <tr>
                    <th scope="col">Level</th>
                    <th scope="col" className="is-num">Tests taken</th>
                    <th scope="col" className="is-num">Average</th>
                  </tr>
                </thead>
                <tbody>
                  {report.by_level.map((row) => (
                    <tr key={row.level}>
                      <td className="vmt-cell-main">{levelLabel(row.level)}</td>
                      <td className="is-num">{row.attempts}</td>
                      <td className="is-num">{formatScore(row.average_score)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  );
}
