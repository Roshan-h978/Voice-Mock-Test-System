import { useEffect, useRef, useState } from 'react';
import { Bell, ClipboardList, MessageSquare, Sparkles } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useNotifications } from '../context/NotificationContext';
import { getNotifications, markAllRead, markRead } from '../services/notificationService';
import { timeAgo } from '../utils/formatters';

export const KIND_ICONS = { review_published: MessageSquare, test_published: Sparkles, review_needed: ClipboardList };

/** Bell in the top bar: unread count, and the latest notifications in a small panel. */
export default function NotificationBell({ allPath }) {
  const { unread, setUnread, refresh } = useNotifications();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState(null);
  const wrapRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return undefined;
    let active = true;
    getNotifications({ page_size: 6 })
      .then((data) => active && setItems(data.results))
      .catch(() => active && setItems([]));
    const close = (event) => {
      if (event.type === 'keydown' ? event.key === 'Escape' : !wrapRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', close);
    return () => {
      active = false;
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', close);
    };
  }, [open]);

  const openItem = async (item) => {
    setOpen(false);
    if (!item.is_read) {
      setUnread((count) => Math.max(0, count - 1));
      markRead(item.id).catch(() => {});
    }
    if (item.link) navigate(item.link);
  };

  const readAll = async () => {
    await markAllRead().catch(() => {});
    setItems((list) => list?.map((item) => ({ ...item, is_read: true })));
    setUnread(0);
    refresh();
  };

  return (
    <div className="vmt-bell" ref={wrapRef}>
      <button
        type="button"
        className="vmt-icon-btn vmt-bell-btn"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="true"
        aria-label={unread ? `Notifications, ${unread} unread` : 'Notifications'}
      >
        <Bell className="vmt-icon" aria-hidden="true" />
        {unread > 0 && (
          <span className="vmt-bell-count" aria-hidden="true">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="vmt-bell-panel" role="region" aria-label="Latest notifications">
          <div className="vmt-bell-head">
            <span className="title-sm">Notifications</span>
            {unread > 0 && (
              <button type="button" className="vmt-link vmt-link-button" onClick={readAll}>
                Mark all as read
              </button>
            )}
          </div>
          {items === null && <p className="body-sm vmt-muted vmt-bell-empty">Loading…</p>}
          {items?.length === 0 && <p className="body-sm vmt-muted vmt-bell-empty">You're all caught up.</p>}
          {items?.length > 0 && (
            <ul className="vmt-bell-list">
              {items.map((item) => {
                const Icon = KIND_ICONS[item.kind] || Bell;
                return (
                  <li key={item.id}>
                    <button type="button" className={`vmt-note${item.is_read ? '' : ' is-unread'}`} onClick={() => openItem(item)}>
                      <span className="vmt-note-icon" aria-hidden="true">
                        <Icon className="vmt-icon-sm" />
                      </span>
                      <span className="vmt-note-text">
                        <span className="vmt-note-title">{item.title}</span>
                        {item.body && <span className="vmt-note-body">{item.body}</span>}
                        <span className="vmt-note-time">{timeAgo(item.created_at)}</span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          <Link to={allPath} className="vmt-bell-all" onClick={() => setOpen(false)}>
            See all notifications
          </Link>
        </div>
      )}
    </div>
  );
}
