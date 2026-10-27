import { Inbox } from 'lucide-react';

/** Friendly placeholder for empty lists. */
export default function EmptyState({ icon: Icon = Inbox, title, children, action }) {
  return (
    <div className="vmt-empty">
      <span className="vmt-empty-icon" aria-hidden="true">
        <Icon className="vmt-icon-lg" />
      </span>
      <p className="title-sm">{title}</p>
      {children && <p className="body-sm">{children}</p>}
      {action && <div style={{ marginTop: 'var(--space-1)' }}>{action}</div>}
    </div>
  );
}
