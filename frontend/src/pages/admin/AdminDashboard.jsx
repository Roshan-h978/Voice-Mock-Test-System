import { useCallback, useEffect, useState } from 'react';
import { Award, ClipboardList, KeyRound, Mail, MessageSquare, Plus, UserPlus, Users } from 'lucide-react';
import Alert from '../../components/Alert';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import LoadingSpinner from '../../components/LoadingSpinner';
import PageHeader from '../../components/PageHeader';
import SkillBar from '../../components/SkillBar';
import StatCard from '../../components/StatCard';
import StatusBadge from '../../components/StatusBadge';
import { useAuth } from '../../context/AuthContext';
import { getDashboard, getEvaluationConfig, sendTestEmail } from '../../services/adminService';
import { getErrorMessage } from '../../services/api';
import { SKILLS } from '../../utils/constants';
import { formatChange, formatDate, formatScore, pluralize } from '../../utils/formatters';

function ScoringStatus({ config }) {
  if (!config) return null;
  if (config.demo_mode) {
    return (
      <Alert tone="warning" title="Demo scoring is on">
        Answers get sample scores. For real scoring, set EVALUATION_DEMO_MODE=False and add OPENAI_API_KEY and
        ANTHROPIC_API_KEY in backend/.env, then restart the backend.
      </Alert>
    );
  }
  if (!config.speech_to_text_ready || !config.feedback_ready) {
    return (
      <Alert tone="danger" title="Scoring isn't set up">
        Add {!config.speech_to_text_ready ? 'OPENAI_API_KEY' : ''}
        {!config.speech_to_text_ready && !config.feedback_ready ? ' and ' : ''}
        {!config.feedback_ready ? 'ANTHROPIC_API_KEY' : ''} to backend/.env and restart the backend. Students can't
        submit answers until then.
      </Alert>
    );
  }
  return null;
}

export default function AdminDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [config, setConfig] = useState(null);
  const [error, setError] = useState('');
  const [emailCheck, setEmailCheck] = useState(null);
  const [sendingEmail, setSendingEmail] = useState(false);

  const handleTestEmail = async () => {
    setSendingEmail(true);
    setEmailCheck(null);
    try {
      const data = await sendTestEmail();
      setEmailCheck({ tone: 'success', text: data.detail });
    } catch (err) {
      setEmailCheck({ tone: 'danger', text: getErrorMessage(err, 'The test email could not be sent.') });
    } finally {
      setSendingEmail(false);
    }
  };

  const load = useCallback(async () => {
    setError('');
    try {
      const [dashboard, evaluation] = await Promise.all([getDashboard(), getEvaluationConfig()]);
      setStats(dashboard);
      setConfig(evaluation);
    } catch (err) {
      setError(getErrorMessage(err, 'The dashboard could not be loaded.'));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <PageHeader
        overline="Admin"
        title="Dashboard"
        subtitle="How your students are doing this week."
        actions={
          <>
            <Button variant="secondary" icon={UserPlus} to="/admin/students?invite=1">
              Invite student
            </Button>
            <Button icon={Plus} to="/admin/tests?new=1">
              New test
            </Button>
          </>
        }
      />

      {user?.uses_default_password && (
        <div className="vmt-banner" style={{ background: 'var(--warning-tint)' }}>
          <div className="vmt-stack vmt-stack-sm">
            <span className="title-sm">You're still using the starting password</span>
            <span className="body-sm vmt-muted">Anyone who knows "admin123" could sign in as you. Choose your own password now.</span>
          </div>
          <Button to="/admin/profile" icon={KeyRound}>
            Change password
          </Button>
        </div>
      )}
      <ScoringStatus config={config} />
      {error && <Alert tone="danger">{error}</Alert>}
      {!stats && !error && <LoadingSpinner label="Loading the dashboard…" />}

      {stats && (
        <>
          <div className="vmt-grid">
            <StatCard
              label="Active students"
              value={stats.students.total}
              sub={`${stats.students.new_this_week} new this week`}
              icon={Users}
            />
            <StatCard
              label="Tests taken this week"
              value={stats.attempts.this_week}
              sub={formatChange(stats.attempts.change_percent) || `${stats.attempts.last_week} last week`}
              icon={ClipboardList}
            />
            <StatCard
              label="Average score this week"
              value={formatScore(stats.average_score.this_week)}
              sub={`Last week: ${formatScore(stats.average_score.last_week)}`}
              icon={Award}
            />
            <StatCard
              label="Waiting for review"
              value={stats.needs_review}
              sub={`${pluralize(stats.published_tests, 'published test')}`}
              icon={MessageSquare}
            />
          </div>

          {stats.needs_review > 0 && (
            <div className="vmt-banner">
              <div className="vmt-stack vmt-stack-sm">
                <span className="title-sm">{pluralize(stats.needs_review, 'test needs', 'tests need')} your review</span>
                <span className="body-sm vmt-muted">Low scores, very short answers and unclear audio are flagged for a teacher.</span>
              </div>
              <Button to="/admin/reviews" icon={MessageSquare}>
                Open review queue
              </Button>
            </div>
          )}

          <div className="vmt-split">
            <section className="vmt-stack" aria-labelledby="recent-title">
              <h2 id="recent-title" className="title-md">
                Recent tests
              </h2>
              {stats.recent_attempts.length === 0 ? (
                <div className="vmt-card">
                  <EmptyState icon={ClipboardList} title="No tests taken yet">
                    When students finish a test, it appears here.
                  </EmptyState>
                </div>
              ) : (
                <div className="vmt-table-wrap">
                  <table className="vmt-table">
                    <thead>
                      <tr>
                        <th scope="col">Student</th>
                        <th scope="col">Test</th>
                        <th scope="col" className="is-num">Score</th>
                        <th scope="col">Status</th>
                        <th scope="col">Date</th>
                        <th scope="col" className="is-actions">
                          <span className="sr-only">Actions</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.recent_attempts.map((item) => (
                        <tr key={item.id}>
                          <td className="vmt-cell-main">{item.student_name}</td>
                          <td>{item.test_title}</td>
                          <td className="is-num">{formatScore(item.overall)}</td>
                          <td>
                            <StatusBadge kind="attempt" status={item.status} />
                          </td>
                          <td>{formatDate(item.submitted_at)}</td>
                          <td className="is-actions">
                            <Button size="sm" variant="secondary" to={`/admin/reviews/${item.id}`}>
                              Open
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <aside className="vmt-card vmt-stack">
              <h2 className="title-sm">Skills this week</h2>
              {stats.attempts.this_week === 0 ? (
                <p className="body-sm vmt-muted">Skill averages appear after students finish tests this week.</p>
              ) : (
                SKILLS.map((skill) => <SkillBar key={skill.key} label={skill.label} value={stats.skills_this_week[skill.key]} />)
              )}
              <hr className="vmt-divider" />
              <Button variant="ghost" to="/admin/reports">
                Open reports
              </Button>
              <hr className="vmt-divider" />
              <h2 className="title-sm">Setup check</h2>
              {config && (
                <p className="body-sm vmt-muted">
                  Scoring: {config.demo_mode ? 'demo mode' : `${config.transcribe_model} + ${config.scoring_model}`}. Review below{' '}
                  {config.review_threshold}%.
                </p>
              )}
              {emailCheck && <Alert tone={emailCheck.tone}>{emailCheck.text}</Alert>}
              <Button variant="secondary" icon={Mail} loading={sendingEmail} onClick={handleTestEmail}>
                Send me a test email
              </Button>
            </aside>
          </div>
        </>
      )}
    </>
  );
}
