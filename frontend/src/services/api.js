// Axios client for the Django API: adds the access token, refreshes it when it
// expires, and turns API errors into plain messages for the screen.

import axios from 'axios';
import { SESSION_EXPIRED_EVENT, STORAGE_KEYS } from '../utils/constants';

export const API_BASE_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

// ---------------------------------------------------------------------------
// Token storage (localStorage, guarded for private windows)
// ---------------------------------------------------------------------------
function readStorage(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key, value) {
  try {
    if (value) window.localStorage.setItem(key, value);
    else window.localStorage.removeItem(key);
  } catch {
    /* storage unavailable: the session lasts until the tab closes */
  }
}

export const tokenStore = {
  getAccess: () => readStorage(STORAGE_KEYS.access),
  getRefresh: () => readStorage(STORAGE_KEYS.refresh),
  set({ access, refresh }) {
    if (access) writeStorage(STORAGE_KEYS.access, access);
    if (refresh) writeStorage(STORAGE_KEYS.refresh, refresh);
  },
  clear() {
    writeStorage(STORAGE_KEYS.access, null);
    writeStorage(STORAGE_KEYS.refresh, null);
  },
  hasSession: () => Boolean(readStorage(STORAGE_KEYS.access) || readStorage(STORAGE_KEYS.refresh)),
};

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // scoring an answer can take a few seconds
});

api.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

const PUBLIC_AUTH_PATHS = ['/auth/login/', '/auth/register/', '/auth/refresh/', '/auth/password-reset/', '/auth/google/'];
let refreshRequest = null;

async function refreshAccessToken() {
  const refresh = tokenStore.getRefresh();
  if (!refresh) throw new Error('No refresh token');
  try {
    const { data } = await axios.post(`${API_BASE_URL}/auth/refresh/`, { refresh });
    tokenStore.set({ access: data.access, refresh: data.refresh || refresh });
    return data.access;
  } catch (error) {
    // Another tab may have refreshed the session at the same moment (each refresh token works once).
    // Its new tokens are already saved, so use them instead of signing the person out.
    const latest = tokenStore.getRefresh();
    if (latest && latest !== refresh && tokenStore.getAccess()) return tokenStore.getAccess();
    throw error;
  }
}

function endSession() {
  tokenStore.clear();
  window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const isPublicCall = PUBLIC_AUTH_PATHS.some((path) => original?.url?.startsWith(path));

    if (error.response?.status === 401 && original && !original._retried && !isPublicCall) {
      // Signed out in another tab: nothing to refresh, so go back to the sign-in page.
      if (!tokenStore.getRefresh()) {
        endSession();
        return Promise.reject(error);
      }
      original._retried = true;
      try {
        refreshRequest = refreshRequest || refreshAccessToken().finally(() => { refreshRequest = null; });
        const access = await refreshRequest;
        original.headers.Authorization = `Bearer ${access}`;
        return api(original);
      } catch {
        endSession();
      }
    }
    return Promise.reject(error);
  },
);

export default api;

// ---------------------------------------------------------------------------
// Error helpers
// ---------------------------------------------------------------------------
function flatten(value) {
  if (Array.isArray(value)) return value.map(flatten).join(' ');
  if (value && typeof value === 'object') return Object.values(value).map(flatten).join(' ');
  return value === undefined || value === null ? '' : String(value);
}

/** One readable sentence for any API error. */
export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (!error?.response) {
    if (error?.code === 'ECONNABORTED') return 'The server took too long to answer. Please try again.';
    return 'We could not reach the server. Check your connection and try again.';
  }
  const { data, status } = error.response;
  if (status >= 500 && (typeof data !== 'object' || !data?.detail)) return 'The server had a problem. Please try again in a moment.';
  if (!data || typeof data !== 'object' || data instanceof Blob) return fallback;
  if (data.detail) return flatten(data.detail);
  if (data.non_field_errors) return flatten(data.non_field_errors);
  const first = Object.values(data)[0];
  return flatten(first) || fallback;
}

/** { field: "message" } for showing errors under form fields. */
export function getFieldErrors(error) {
  const data = error?.response?.data;
  if (!data || typeof data !== 'object' || Array.isArray(data)) return {};
  return Object.fromEntries(
    Object.entries(data)
      .filter(([key]) => key !== 'detail' && key !== 'non_field_errors')
      .map(([key, value]) => [key, flatten(value)]),
  );
}
