import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as authService from '../services/authService';
import { tokenStore } from '../services/api';
import { SESSION_EXPIRED_EVENT } from '../utils/constants';

const AuthContext = createContext(null);

/** Holds the signed-in user and the sign-in / sign-out actions for the whole app. */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore the session on page load.
  useEffect(() => {
    let active = true;
    if (!authService.hasSession()) {
      setLoading(false);
      return undefined;
    }
    authService
      .getMe()
      .then((me) => active && setUser(me))
      .catch((error) => {
        if (error.response?.status === 401) tokenStore.clear();
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  // The API client fires this event when the session can't be refreshed.
  useEffect(() => {
    const handleExpired = () => setUser(null);
    window.addEventListener(SESSION_EXPIRED_EVENT, handleExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handleExpired);
  }, []);

  const login = useCallback(async (email, password) => {
    const signedIn = await authService.login(email, password);
    setUser(signedIn);
    return signedIn;
  }, []);

  const loginWithGoogle = useCallback(async (credential, inviteToken) => {
    const signedIn = await authService.loginWithGoogle(credential, inviteToken);
    setUser(signedIn);
    return signedIn;
  }, []);

  const register = useCallback(async (payload) => {
    const created = await authService.register(payload);
    setUser(created);
    return created;
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const me = await authService.getMe();
    setUser(me);
    return me;
  }, []);

  const value = useMemo(
    () => ({ user, loading, isAuthenticated: Boolean(user), login, loginWithGoogle, register, logout, refreshUser, setUser }),
    [user, loading, login, loginWithGoogle, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>.');
  return context;
}
