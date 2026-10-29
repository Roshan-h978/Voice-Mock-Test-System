import { useEffect, useState } from 'react';
import { Bell, CheckCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Alert from '../../components/Alert';
import Button from '../../components/Button';
import EmptyState from '../../components/EmptyState';
import LoadingSpinner from '../../components/LoadingSpinner';
import { KIND_ICONS } from '../../components/NotificationBell';
import PageHeader from '../../components/PageHeader';
import { useNotifications } from '../../context/NotificationContext';
import { getErrorMessage } from '../../services/api';
import { getNotifications, markAllRead, markRead } from '../../services/notificationService';
import { formatDateTime, timeAgo } from '../../utils/formatters';

const TABS = [
  { value: '', label: 'All' },
  { value: '1', label: 'Unread' },
];

/** Every notification for the signed-in student or admin, newest first. */
export default function Notifications() {
  const { unread, setUnread, refresh } = useNotifications();
  const navigate = useNavigate();
  const [filter, setFilter] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setError('');
    getNotifications({ unread: filter || undefined, page, page_size: 20 })
      .then((response) => {
        if (!active) return;
        setData(response);
        if (response.page && response.page !== page) setPage(response.page);
      })
      .catch((err) => active && setError(getErrorMessage(err, 'Notifications could not be loaded.')));
    return () => {
      active = false;
    };
  }, [filter, page, reload]);

  const open = (item) => {
    if (!item.is_read) {
      setUnread((count) => Math.max(0, count - 1));
      markRead(item.id).catch(() => {});
    }
    if (item.link) navigate(item.link);
    else setReload((value) => value + 1);
  };

  const readAll = async () => {
    try {
      await markAllRead();
      setUnread(0);
      refresh();
      setReload((value) => value + 1);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <>
      <PageHeader
        overline="Inbox"
        title="Notifications"
        subtitle="Teacher reviews, new tests and other updates."
        actions={
          unread > 0 && (
            <Button variant="secondary" icon={CheckCheck} onClick={readAll}>
              Mark all as read
            </Button>
          )
        }
      />
      <div className="vmt-tabs" role="tablist" aria-label="Show">
        {TABS.map((tab) => (
          <button
            key={tab.label}
            type="button"
            role="tab"
            aria-selected={filter === tab.value}
            className={`vmt-tab${filter === tab.value ? ' is-active' : ''}`}
            onClick={() => {
              setFilter(tab.value);
              setPage(1);
            }}
          >
            {tab.label}
            {tab.value && unread > 0 ? ` (${unread})` : ''}
          </button>
        ))}
      </div>

      {error && <Alert tone="danger">{error}</Alert>}
      {!data && !error && <LoadingSpinner label="Loading notifications…" />}
      {data && data.results.length === 0 && (
        <div className="vmt-card">
          <EmptyState icon={Bell} title={filter ? 'No unread notifications' : 'No notifications yet'}>
            {filter ? "You're all caught up." : "When a teacher reviews your test or a new test is published, you'll see it here."}
          </EmptyState>
        </div>
      )}
      {data && data.results.length > 0 && (
        <ul className="vmt-notes">
          {data.results.map((item) => {
            const Icon = KIND_ICONS[item.kind] || Bell;
            return (
              <li key={item.id}>
                <button type="button" className={`vmt-note vmt-card${item.is_read ? '' : ' is-unread'}`} onClick={() => open(item)}>
                  <span className="vmt-note-icon" aria-hidden="true">
                    <Icon className="vmt-icon" />
                  </span>
                  <span className="vmt-note-text">
                    <span className="vmt-note-title">{item.title}</span>
                    {item.body && <span className="vmt-note-body">{item.body}</span>}
                    <span className="vmt-note-time" title={formatDateTime(item.created_at)}>
                      {timeAgo(item.created_at)}
                      {!item.is_read && <span className="vmt-note-new">New</span>}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {data && data.pages > 1 && (
        <div className="vmt-pagination">
          <span className="body-sm vmt-muted">
            Page {page} of {data.pages}
          </span>
          <div className="vmt-row vmt-row-tight">
            <Button size="sm" variant="secondary" disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>
              Previous
            </Button>
            <Button size="sm" variant="secondary" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
