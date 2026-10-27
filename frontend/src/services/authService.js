// Sign-in, sign-up, profile and password requests.

import api, { tokenStore } from './api';

export async function login(email, password) {
  const { data } = await api.post('/auth/login/', { email, password });
  tokenStore.set(data);
  return data.user;
}

/** Sign in (or sign up) with the ID token from Google's button. */
export async function loginWithGoogle(credential, inviteToken) {
  const { data } = await api.post('/auth/google/', { credential, ...(inviteToken ? { invite_token: inviteToken } : {}) });
  tokenStore.set(data);
  return data.user;
}

let googleConfigRequest = null;

/** { enabled, client_id, setup_hint } — asked once per page load. */
export function getGoogleConfig() {
  googleConfigRequest =
    googleConfigRequest ||
    api
      .get('/auth/google/config/')
      .then((response) => response.data)
      .catch(() => {
        googleConfigRequest = null;
        return { enabled: false, client_id: null, setup_hint: false };
      });
  return googleConfigRequest;
}

/** payload: { full_name, email, password, invite_token? } */
export async function register(payload) {
  const { data } = await api.post('/auth/register/', payload);
  tokenStore.set(data);
  return data.user;
}

export async function logout() {
  const refresh = tokenStore.getRefresh();
  try {
    if (refresh) await api.post('/auth/logout/', { refresh });
  } catch {
    /* the session ends locally either way */
  } finally {
    tokenStore.clear();
  }
}

export async function getMe() {
  const { data } = await api.get('/auth/me/');
  return data;
}

/** payload: { full_name?, phone?, level? } */
export async function updateMe(payload) {
  const { data } = await api.patch('/auth/me/', payload);
  return data;
}

export async function changePassword(currentPassword, newPassword) {
  const { data } = await api.post('/auth/me/password/', {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return data;
}

export async function requestPasswordReset(email) {
  const { data } = await api.post('/auth/password-reset/', { email });
  return data;
}

export async function confirmPasswordReset(token, newPassword) {
  const { data } = await api.post('/auth/password-reset/confirm/', { token, new_password: newPassword });
  return data;
}

export async function getInvitation(token) {
  const { data } = await api.get(`/auth/invitations/${encodeURIComponent(token)}/`);
  return data;
}

export const hasSession = () => tokenStore.hasSession();
