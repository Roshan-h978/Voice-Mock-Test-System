import { Check } from 'lucide-react';
import Brand from './Brand';

const POINTS = [
  'Speaking tests with real exam-style questions',
  'Scores for fluency, pronunciation and grammar',
  'Clear tips you can use in your next answer',
];

/** Two-column layout for sign-in, sign-up and password pages. */
export default function AuthShell({ title, subtitle, children }) {
  return (
    <div className="vmt-auth">
      <aside className="vmt-auth-hero">
        <Brand />
        <div className="vmt-stack vmt-stack-lg">
          <h2 className="display">Practise speaking English with confidence.</h2>
          <ul className="vmt-checklist vmt-hide-sm">
            {POINTS.map((point) => (
              <li key={point}>
                <span className="vmt-check-icon" aria-hidden="true">
                  <Check className="vmt-icon-sm" />
                </span>
                {point}
              </li>
            ))}
          </ul>
        </div>
        <span className="caption vmt-hide-sm" style={{ color: 'var(--on-navy-muted)' }}>
          Your recordings are only used to score your answers.
        </span>
      </aside>
      <main className="vmt-auth-panel">
        <div className="vmt-auth-form">
          <div className="vmt-stack vmt-stack-sm">
            <h1 className="title-lg">{title}</h1>
            {subtitle && <p className="body vmt-muted">{subtitle}</p>}
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}
