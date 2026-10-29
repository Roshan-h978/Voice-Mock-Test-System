import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { getUnreadCount } from '../services/notificationService';

const NotificationContext = createContext({ unread: 0, refresh: () => {}, setUnread: () => {} });

const POLL_MS = 60000;

/** Keeps the unread count for the bell and the sidebar: on every page change and once a minute. */
export function NotificationProvider({ children }) {
  const [unread, setUnread] = useState(0);
  const { pathname } = useLocation();

  const refresh = useCallback(() => {
    getUnreadCount()
      .then(setUnread)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh, pathname]);

  useEffect(() => {
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') refresh();
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  const value = useMemo(() => ({ unread, refresh, setUnread }), [unread, refresh]);
  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}

export function useNotifications() {
  return useContext(NotificationContext);
}
