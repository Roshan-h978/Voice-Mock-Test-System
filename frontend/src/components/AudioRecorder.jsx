import { useEffect, useRef } from 'react';
import { Check, Mic, RotateCcw, Square } from 'lucide-react';
import useAudioRecorder from '../hooks/useAudioRecorder';
import { formatDuration } from '../utils/formatters';
import Alert from './Alert';
import Button from './Button';

const BAR_SHAPE = [0.35, 0.6, 0.85, 0.5, 1, 0.7, 0.45, 0.9, 0.6, 0.8, 0.4, 0.65];

const STATUS_TEXT = {
  idle: 'Press the button and start speaking.',
  requesting: 'Waiting for microphone permission…',
  recording: 'Recording. Press the button to stop.',
  recorded: 'Listen to your recording, or record it again.',
  error: '',
};

/**
 * Record button + timer + live level + playback.
 * onChange receives { blob, duration } when a recording is ready, and null when it is cleared.
 * Remount it with a new `key` to start fresh (for example for the next question).
 */
export default function AudioRecorder({ maxSeconds = 60, onChange, disabled = false, compact = false }) {
  const { status, seconds, duration, audioBlob, audioUrl, error, level, isSupported, start, stop, reset } =
    useAudioRecorder({ maxSeconds });

  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    onChangeRef.current?.(status === 'recorded' && audioBlob ? { blob: audioBlob, duration } : null);
  }, [status, audioBlob, duration]);

  if (!isSupported) {
    return (
      <Alert tone="warning" title="Recording isn't available in this browser">
        Please open the app in the latest Chrome, Edge, Firefox or Safari. On a phone, use the browser app rather than an
        in-app browser.
      </Alert>
    );
  }

  const recording = status === 'recording';
  const recorded = status === 'recorded';
  const secondsLeft = maxSeconds - seconds;

  const handleMainButton = () => {
    if (recording) stop();
    else if (!recorded) start();
  };

  let mainLabel = 'Start recording';
  let MainIcon = Mic;
  if (recording) {
    mainLabel = 'Stop recording';
    MainIcon = Square;
  } else if (recorded) {
    mainLabel = 'Recording saved';
    MainIcon = Check;
  }

  return (
    <div className="vmt-recorder">
      <button
        type="button"
        className={`vmt-record${compact ? ' vmt-record-sm' : ''}${recording ? ' is-recording' : ''}${recorded ? ' is-done' : ''}`}
        onClick={handleMainButton}
        disabled={disabled || status === 'requesting' || recorded}
        aria-label={mainLabel}
        aria-pressed={recording}
      >
        <MainIcon className={compact ? 'vmt-icon-lg' : 'vmt-icon-xl'} aria-hidden="true" />
      </button>

      <div className="vmt-wave" aria-hidden="true">
        {BAR_SHAPE.map((shape, index) => (
          <span
            key={index}
            style={{
              height: recording ? `${Math.max(12, Math.min(100, level * 100 * shape + 12))}%` : recorded ? '50%' : '20%',
              background: recording ? 'var(--teal)' : recorded ? 'var(--navy)' : undefined,
            }}
          />
        ))}
      </div>

      <div className={`vmt-timer${compact ? ' vmt-timer-sm' : ''}`} aria-hidden="true">
        {formatDuration(seconds)}
        {!compact && <span className="body vmt-muted"> / {formatDuration(maxSeconds)}</span>}
      </div>

      <p className="body-sm vmt-muted" aria-live="polite">
        {recording && secondsLeft <= 10 && !compact ? `${secondsLeft} seconds left. ` : ''}
        {STATUS_TEXT[status]}
      </p>

      {error && <Alert tone="danger">{error}</Alert>}

      {recorded && audioUrl && (
        <div className="vmt-stack vmt-stack-sm vmt-playback">
          <audio src={audioUrl} controls preload="metadata" aria-label="Your recording" />
          <div className="vmt-row vmt-row-tight" style={{ justifyContent: 'center' }}>
            <Button variant="secondary" size="sm" icon={RotateCcw} onClick={reset} disabled={disabled}>
              Record again
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
