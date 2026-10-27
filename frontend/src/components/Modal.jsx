import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

/** Dialog over the page. Closes with Escape, the X button or a click on the backdrop. */
export default function Modal({ open, title, description, onClose, children, footer, wide = false }) {
  const titleId = useId();
  const dialogRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return undefined;
    const previouslyFocused = document.activeElement;
    const handleKey = (event) => {
      if (event.key === 'Escape') onCloseRef.current?.();
    };
    document.addEventListener('keydown', handleKey);
    document.body.style.overflow = 'hidden';
    const firstField = dialogRef.current?.querySelector('input, select, textarea');
    (firstField || dialogRef.current)?.focus();

    return () => {
      document.removeEventListener('keydown', handleKey);
      document.body.style.overflow = '';
      previouslyFocused?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      className="vmt-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCloseRef.current?.();
      }}
    >
      <div
        ref={dialogRef}
        className={`vmt-modal${wide ? ' vmt-modal-wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
      >
        <div className="vmt-modal-head">
          <div className="vmt-stack vmt-stack-sm">
            <h2 id={titleId} className="title-md">
              {title}
            </h2>
            {description && <p className="body-sm vmt-muted">{description}</p>}
          </div>
          {onClose && (
            <button type="button" className="vmt-icon-btn vmt-icon-btn-sm" onClick={onClose} aria-label="Close">
              <X className="vmt-icon" aria-hidden="true" />
            </button>
          )}
        </div>
        {children}
        {footer && <div className="vmt-modal-actions">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}
