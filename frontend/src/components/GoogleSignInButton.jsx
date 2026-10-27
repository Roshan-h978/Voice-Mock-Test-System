import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getErrorMessage } from '../services/api';
import { getGoogleConfig } from '../services/authService';
import { homeFor } from '../utils/constants';
import Alert from './Alert';

const GIS_SCRIPT = 'https://accounts.google.com/gsi/client';
let scriptRequest = null;

/** Loads Google Identity Services once per page. */
function loadGoogleScript() {
  if (window.google?.accounts?.id) return Promise.resolve(window.google);
  scriptRequest =
    scriptRequest ||
    new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = GIS_SCRIPT;
      script.async = true;
      script.defer = true;
      const fail = (message) => {
        scriptRequest = null;
        script.remove();
        reject(new Error(message));
      };
      // A blocked or very slow connection: stop waiting and show the message instead of an empty space.
      const timer = setTimeout(() => fail('Google script took too long to load'), 15000);
      script.onload = () => {
        clearTimeout(timer);
        if (window.google?.accounts?.id) resolve(window.google);
        else fail('Google script loaded without the sign-in library');
      };
      script.onerror = () => {
        clearTimeout(timer);
        fail('Google script could not load');
      };
      document.head.appendChild(script);
    });
  return scriptRequest;
}

/**
 * "Continue with Google" using Google's own button.
 * The client ID comes from the backend (GOOGLE_CLIENT_ID in backend/.env); without it the button is hidden.
 * text: 'continue_with' | 'signup_with' | 'signin_with'
 */
export default function GoogleSignInButton({ text = 'continue_with', inviteToken = '', onError }) {
  const { loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const containerRef = useRef(null);
  const [config, setConfig] = useState(null);
  const [state, setState] = useState('idle'); // idle | ready | busy | unavailable
  const [error, setError] = useState('');

  // Always call the latest version of the handler from Google's callback.
  const handlerRef = useRef(null);
  handlerRef.current = async ({ credential }) => {
    setState('busy');
    setError('');
    try {
      const user = await loginWithGoogle(credential, inviteToken);
      navigate(homeFor(user, location.state?.from?.pathname), { replace: true });
    } catch (err) {
      const message = getErrorMessage(err, "Google sign-in didn't work. Please try again.");
      setError(message);
      onError?.(message);
      setState('ready');
    }
  };

  useEffect(() => {
    let active = true;
    getGoogleConfig().then((data) => active && setConfig(data));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!config?.enabled || !containerRef.current) return undefined;
    let active = true;
    loadGoogleScript()
      .then((google) => {
        if (!active || !containerRef.current) return;
        google.accounts.id.initialize({
          client_id: config.client_id,
          callback: (response) => handlerRef.current(response),
          ux_mode: 'popup',
          auto_select: false,
          cancel_on_tap_outside: true,
        });
        const width = Math.max(200, Math.min(400, Math.floor(containerRef.current.offsetWidth || 400)));
        google.accounts.id.renderButton(containerRef.current, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          shape: 'rectangular',
          text,
          logo_alignment: 'left',
          width,
        });
        setState('ready');
      })
      .catch(() => active && setState('unavailable'));
    return () => {
      active = false;
    };
  }, [config, text]);

  if (!config || (!config.enabled && !config.setup_hint)) return null;

  return (
    <div className="vmt-google">
      {config.enabled ? (
        <>
          <div ref={containerRef} className="vmt-google-button" aria-busy={state === 'busy' || undefined} />
          {state === 'busy' && <p className="caption vmt-muted">Signing you in with Google…</p>}
          {state === 'unavailable' && (
            <p className="caption vmt-muted">Google sign-in couldn't load. Check your connection, or use your email and password.</p>
          )}
          {error && <Alert tone="danger">{error}</Alert>}
        </>
      ) : (
        <div className="vmt-google-hint">
          <span className="label">Google sign-in is off</span>
          <span className="caption vmt-muted">
            Add your GOOGLE_CLIENT_ID to backend/.env and restart the backend to show the Google button here. (Only shown
            in development.)
          </span>
        </div>
      )}
      <div className="vmt-or" role="separator">
        <span>or use your email</span>
      </div>
    </div>
  );
}
