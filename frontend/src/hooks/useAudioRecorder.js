import { useCallback, useEffect, useRef, useState } from 'react';

const MIME_CANDIDATES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];

export function pickMimeType() {
  if (typeof window === 'undefined' || !window.MediaRecorder?.isTypeSupported) return '';
  return MIME_CANDIDATES.find((type) => window.MediaRecorder.isTypeSupported(type)) || '';
}

export function isRecordingSupported() {
  return typeof window !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia) && Boolean(window.MediaRecorder);
}

function friendlyError(error) {
  switch (error?.name) {
    case 'NotAllowedError':
    case 'SecurityError':
      return 'Microphone access is blocked. Allow the microphone in your browser (the icon in the address bar), then try again.';
    case 'NotFoundError':
    case 'OverconstrainedError':
      return 'No microphone was found. Connect one and try again.';
    case 'NotReadableError':
      return 'Your microphone is being used by another app. Close that app and try again.';
    default:
      return 'Recording could not start. Please try again.';
  }
}

/**
 * Records audio from the microphone with the MediaRecorder API.
 *
 * status: idle | requesting | recording | recorded | error
 * Recording stops on its own after maxSeconds.
 */
export default function useAudioRecorder({ maxSeconds = 60 } = {}) {
  const [status, setStatus] = useState('idle');
  const [seconds, setSeconds] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState('');
  const [error, setError] = useState('');
  const [level, setLevel] = useState(0);

  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const startedAtRef = useRef(0);
  const audioContextRef = useRef(null);
  const frameRef = useRef(null);
  const urlRef = useRef('');
  const mountedRef = useRef(false);
  const maxSecondsRef = useRef(maxSeconds);
  maxSecondsRef.current = maxSeconds;

  const releaseMicrophone = useCallback(() => {
    clearInterval(timerRef.current);
    cancelAnimationFrame(frameRef.current);
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
    }
    audioContextRef.current = null;
    setLevel(0);
  }, []);

  const clearRecording = useCallback(() => {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    urlRef.current = '';
    setAudioBlob(null);
    setAudioUrl('');
    setSeconds(0);
    setDuration(0);
  }, []);

  const stop = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== 'inactive') recorder.stop();
  }, []);

  const startLevelMeter = useCallback((stream) => {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    const context = new AudioContextClass();
    const analyser = context.createAnalyser();
    analyser.fftSize = 512;
    context.createMediaStreamSource(stream).connect(analyser);
    audioContextRef.current = context;
    const samples = new Uint8Array(analyser.fftSize);
    let lastUpdate = 0;

    const tick = (now) => {
      analyser.getByteTimeDomainData(samples);
      if (now - lastUpdate > 80) {
        let sum = 0;
        for (let i = 0; i < samples.length; i += 1) {
          const centered = (samples[i] - 128) / 128;
          sum += centered * centered;
        }
        setLevel(Math.min(1, Math.sqrt(sum / samples.length) * 4));
        lastUpdate = now;
      }
      frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
  }, []);

  const start = useCallback(async () => {
    if (!isRecordingSupported()) {
      setError('This browser cannot record audio. Please use the latest Chrome, Edge, Firefox or Safari.');
      setStatus('error');
      return;
    }
    clearRecording();
    setError('');
    setStatus('requesting');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      if (!mountedRef.current) {
        // The page was left while the browser was asking for permission: switch the microphone off again.
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data?.size) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const elapsed = Math.min(maxSecondsRef.current, (Date.now() - startedAtRef.current) / 1000);
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType || 'audio/webm' });
        const url = URL.createObjectURL(blob);
        urlRef.current = url;
        releaseMicrophone();
        setAudioBlob(blob);
        setAudioUrl(url);
        setDuration(elapsed);
        setSeconds(Math.round(elapsed));
        setStatus('recorded');
      };

      recorder.start(250);
      recorderRef.current = recorder;
      startedAtRef.current = Date.now();
      setSeconds(0);
      setStatus('recording');

      timerRef.current = setInterval(() => {
        const elapsed = (Date.now() - startedAtRef.current) / 1000;
        setSeconds(Math.min(maxSecondsRef.current, Math.floor(elapsed)));
        if (elapsed >= maxSecondsRef.current) stop();
      }, 200);
      startLevelMeter(stream);
    } catch (err) {
      releaseMicrophone();
      setError(friendlyError(err));
      setStatus('error');
    }
  }, [clearRecording, releaseMicrophone, startLevelMeter, stop]);

  const reset = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.onstop = null;
      recorder.stop();
    }
    releaseMicrophone();
    clearRecording();
    setError('');
    setStatus('idle');
  }, [clearRecording, releaseMicrophone]);

  // Stop the microphone and free memory when the component goes away.
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== 'inactive') {
        recorder.onstop = null;
        recorder.stop();
      }
      releaseMicrophone();
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    };
  }, [releaseMicrophone]);

  return {
    status,
    isRecording: status === 'recording',
    hasRecording: status === 'recorded' && Boolean(audioBlob),
    seconds,
    duration,
    audioBlob,
    audioUrl,
    error,
    level,
    isSupported: isRecordingSupported(),
    start,
    stop,
    reset,
  };
}
