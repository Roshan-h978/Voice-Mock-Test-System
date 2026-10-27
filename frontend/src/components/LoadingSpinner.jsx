/** Spinner with a short message. `fullScreen` centres it on the whole page. */
export default function LoadingSpinner({ label = 'Loading…', fullScreen = false }) {
  return (
    <div className={`vmt-loading${fullScreen ? ' is-fullscreen' : ''}`} role="status" aria-live="polite">
      <span className="vmt-spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
