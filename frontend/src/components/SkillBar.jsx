import { formatScore } from '../utils/formatters';

/** One skill with its score and a progress bar. */
export default function SkillBar({ label, value, description }) {
  const width = value === null || value === undefined ? 0 : Math.max(0, Math.min(100, value));
  return (
    <div className="vmt-skill">
      <div className="vmt-skill-row">
        <span>{label}</span>
        <span className="vmt-num">{formatScore(value)}</span>
      </div>
      <div
        className="vmt-bar"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value ?? undefined}
      >
        <div className="vmt-bar-fill" style={{ width: `${width}%` }} />
      </div>
      {description && <span className="vmt-meta">{description}</span>}
    </div>
  );
}
