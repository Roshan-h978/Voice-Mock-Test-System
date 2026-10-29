import { useEffect, useState } from 'react';
import { RotateCcw, Trash2 } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import Alert from '../../components/Alert';
import { AnswerFeedback } from '../../components/AnswerDetails';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import Modal from '../../components/Modal';
import PageHeader from '../../components/PageHeader';
import ScoreRing from '../../components/ScoreRing';
import SkillBar from '../../components/SkillBar';
import { getErrorMessage } from '../../services/api';
import { deletePracticeAnswer, getPracticeAnswer } from '../../services/learningService';
import { SKILLS } from '../../utils/constants';
import { formatDateTime, headlineFor } from '../../utils/formatters';

/** One saved Quick practice answer. */
export default function PracticeResult() {
  const { practiceId } = useParams();
  const navigate = useNavigate();
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let active = true;
    getPracticeAnswer(practiceId)
      .then((data) => active && setAnswer(data))
      .catch((err) => active && setError(getErrorMessage(err, 'This practice answer could not be loaded.')));
    return () => {
      active = false;
    };
  }, [practiceId]);

  const remove = async () => {
    setDeleting(true);
    try {
      await deletePracticeAnswer(answer.id);
      navigate('/student/practice', { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  const back = { to: '/student/practice', label: 'Quick practice' };
  if (!answer && error) {
    return (
      <>
        <PageHeader title="Practice answer" back={back} />
        <Alert tone="danger">{error}</Alert>
      </>
    );
  }
  if (!answer) return <LoadingSpinner label="Loading your practice answer…" />;

  const practiseAgain = {
    question: {
      source: answer.source,
      topic: answer.topic,
      topic_label: answer.topic_label,
      question_text: answer.question_text,
      hint: answer.hint,
      time_limit: answer.time_limit,
    },
  };

  return (
    <>
      <PageHeader
        back={back}
        overline={answer.topic_label || 'Practice'}
        title={answer.question_text}
        subtitle={`Practised ${formatDateTime(answer.created_at)}`}
        actions={
          <Button variant="secondary" size="sm" icon={Trash2} onClick={() => setConfirmDelete(true)}>
            Delete
          </Button>
        }
      />
      {error && <Alert tone="danger">{error}</Alert>}
      {answer.is_demo && <Alert tone="warning">This answer was scored in demo mode (sample values).</Alert>}
      <div className="vmt-card vmt-practice-score">
        <ScoreRing value={answer.overall} size="sm" label="Score for this answer" />
        <div className="vmt-stack vmt-stack-sm" style={{ flex: '1 1 260px' }}>
          <h2 className="title-md">{headlineFor(answer.overall)}</h2>
          {SKILLS.map((skill) => (
            <SkillBar key={skill.key} label={skill.label} value={answer[skill.key]} />
          ))}
        </div>
      </div>
      <div className="vmt-card vmt-stack">
        <AnswerFeedback answer={answer} label="Your practice recording" />
      </div>
      <div>
        <Button icon={RotateCcw} to="/student/practice" state={practiseAgain}>
          Practise this question again
        </Button>
      </div>
      <Modal
        open={confirmDelete}
        title="Delete this practice answer?"
        description="The recording and its feedback are removed for good."
        onClose={() => setConfirmDelete(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
            <Button variant="danger" icon={Trash2} loading={deleting} onClick={remove}>
              Delete
            </Button>
          </>
        }
      />
    </>
  );
}
