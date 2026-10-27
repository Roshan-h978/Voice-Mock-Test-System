const RADIUS = 52;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Circular score from 0 to 100. */
export default function ScoreRing({ value, size = 'md', label = 'Overall score' }) {
  const score = value === null || value === undefined ? null : Math.max(0, Math.min(100, Math.round(value)));
  const filled = ((score ?? 0) / 100) * CIRCUMFERENCE;

  return (
    <div
      className={`vmt-ring${size === 'sm' ? ' vmt-ring-sm' : ''}`}
      role="img"
      aria-label={score === null ? `${label}: not scored yet` : `${label}: ${score} out of 100`}
    >
      <svg viewBox="0 0 120 120" aria-hidden="true">
        <circle className="vmt-ring-track" cx="60" cy="60" r={RADIUS} />
        <circle
          className="vmt-ring-fill"
          cx="60"
          cy="60"
          r={RADIUS}
          strokeDasharray={`${filled} ${CIRCUMFERENCE}`}
        />
      </svg>
      <span className="vmt-ring-value" aria-hidden="true">
        {score === null ? '—' : score}
      </span>
    </div>
  );
}
