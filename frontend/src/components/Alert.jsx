import { CircleAlert, CircleCheck, Info, TriangleAlert, X } from 'lucide-react';

const ICONS = { info: Info, success: CircleCheck, warning: TriangleAlert, danger: CircleAlert };

/** Inline message. tone: info | success | warning | danger */
export default function Alert({ tone = 'info', title, children, onClose, className = '' }) {
  const Icon = ICONS[tone] || Info;
  const toneClass = tone === 'warning' ? 'vmt-alert-warning' : tone === 'danger' ? 'vmt-alert-danger' : '';
  return (
    <div className={`vmt-alert ${toneClass} ${className}`.trim()} role={tone === 'danger' ? 'alert' : 'status'}>
      <Icon className="vmt-icon" aria-hidden="true" />
      <div className="vmt-alert-body">
        {title && <span className="vmt-alert-title">{title}</span>}
        {children && <div>{children}</div>}
      </div>
      {onClose && (
        <button type="button" className="vmt-alert-close" onClick={onClose} aria-label="Dismiss message">
          <X className="vmt-icon" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
