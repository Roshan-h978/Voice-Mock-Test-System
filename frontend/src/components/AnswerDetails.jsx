import { Check, ChevronDown } from 'lucide-react';
import { formatDuration, formatScore, pluralize } from '../utils/formatters';
import StatusBadge from './StatusBadge';

/** One answer: recording, transcript, measurements, tip and corrections. Shared with the admin review page. */
export default function AnswerDetails({ answer, actions }) {
  return (
    <details className="vmt-accordion">
      <summary>
        <span className="vmt-accordion-title">
          Question {answer.question_order}: {answer.question_text}
        </span>
        {answer.needs_review && <StatusBadge tone="progress">Check</StatusBadge>}
        <span className="title-sm vmt-num">{formatScore(answer.overall)}</span>
        <ChevronDown className="vmt-icon vmt-accordion-chevron" aria-hidden="true" />
      </summary>
      <div className="vmt-accordion-body">
        {answer.audio_url && <audio src={answer.audio_url} controls preload="none" aria-label={`Recording for question ${answer.question_order}`} />}
        <div className="vmt-stack vmt-stack-sm">
          <span className="label">What we heard</span>
          <p className="vmt-transcript">{answer.transcript || 'No transcript available.'}</p>
        </div>
        <div className="vmt-chips">
          <span className="vmt-chip">Fluency {formatScore(answer.fluency)}</span>
          <span className="vmt-chip">Pronunciation {formatScore(answer.pronunciation)}</span>
          <span className="vmt-chip">Grammar {formatScore(answer.grammar)}</span>
          {answer.words_per_minute !== null && <span className="vmt-chip">{answer.words_per_minute} words a minute</span>}
          <span className="vmt-chip">{pluralize(answer.filler_count, 'filler word')}</span>
          <span className="vmt-chip">{pluralize(answer.long_pauses, 'long pause')}</span>
          {answer.duration_seconds !== null && <span className="vmt-chip">{formatDuration(answer.duration_seconds)} long</span>}
        </div>
        {answer.strengths?.length > 0 && (
          <ul className="vmt-checklist">
            {answer.strengths.map((text, index) => (
              <li key={`${index}-${text}`}>
                <span className="vmt-check-icon" aria-hidden="true">
                  <Check className="vmt-icon-sm" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        )}
        {answer.tip && (
          <div className="vmt-callout vmt-callout-warning">
            <span className="overline">Tip</span>
            <span className="body-sm">{answer.tip}</span>
          </div>
        )}
        {answer.corrections?.length > 0 && (
          <div className="vmt-stack vmt-stack-sm">
            <span className="label">Try saying</span>
            {answer.corrections.map((item, index) => (
              <dl key={`${index}-${item.said}`} className="vmt-correction">
                <dt>You said</dt>
                <dd>“{item.said}”</dd>
                <dt>Better</dt>
                <dd>“{item.better}”</dd>
              </dl>
            ))}
          </div>
        )}
        {answer.review_reasons?.length > 0 && <p className="caption vmt-muted">Flagged: {answer.review_reasons.join(', ')}</p>}
        {actions}
      </div>
    </details>
  );
}
