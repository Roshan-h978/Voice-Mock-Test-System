/*
 * Decorative shapes taken from the app's own parts: the rings around the record button,
 * the waveform shown while recording, and the score ring. All are hidden from screen readers.
 */

const BAR_HEIGHTS = [28, 52, 78, 44, 96, 64, 38, 84, 58, 32, 70, 48, 90, 42, 26];

/** Concentric circles, like sound spreading out from a voice. Colour comes from `color`. */
export function SoundRings({ className = '', rings = 4 }) {
  const radii = Array.from({ length: rings }, (_, index) => 22 + (index * 76) / Math.max(rings - 1, 1));
  return (
    <svg className={`vmt-rings ${className}`.trim()} viewBox="0 0 200 200" aria-hidden="true" focusable="false">
      {radii.map((radius, index) => (
        <circle key={radius} cx="100" cy="100" r={radius} style={{ opacity: 1 - index / (rings + 1) }} />
      ))}
    </svg>
  );
}

/** Rounded bars like a voice waveform. `live` makes them move gently, as if someone is speaking. */
export function Waveform({ className = '', bars = BAR_HEIGHTS, live = false }) {
  return (
    <span className={`vmt-wavebars${live ? ' is-live' : ''} ${className}`.trim()} aria-hidden="true">
      {bars.map((height, index) => (
        // The bars never change order, so their position is a stable key.
        <span key={index} style={{ '--h': `${height}%`, '--i': index }} />
      ))}
    </span>
  );
}

/** Part of a score ring: a thick round-ended arc. `value` is how much of the circle it covers (0–100). */
export function ScoreArc({ className = '', value = 72 }) {
  const circumference = 2 * Math.PI * 44;
  return (
    <svg className={`vmt-arc ${className}`.trim()} viewBox="0 0 100 100" aria-hidden="true" focusable="false">
      <circle cx="50" cy="50" r="44" className="vmt-arc-track" />
      <circle
        cx="50"
        cy="50"
        r="44"
        className="vmt-arc-fill"
        strokeDasharray={`${(circumference * value) / 100} ${circumference}`}
      />
    </svg>
  );
}
