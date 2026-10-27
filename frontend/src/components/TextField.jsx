import { useId, useState } from 'react';

/**
 * Labelled form field with help text and an error message.
 * as: input (default) | textarea | select. Password inputs get a Show/Hide button.
 */
export default function TextField({ label, error, help, as = 'input', type = 'text', className = '', children, id, ...props }) {
  const autoId = useId();
  const fieldId = id || autoId;
  const [showPassword, setShowPassword] = useState(false);
  const describedBy = [help && `${fieldId}-help`, error && `${fieldId}-error`].filter(Boolean).join(' ') || undefined;
  const common = { id: fieldId, 'aria-invalid': Boolean(error) || undefined, 'aria-describedby': describedBy, ...props };

  let control;
  if (as === 'textarea') {
    control = <textarea className="vmt-textarea" {...common} />;
  } else if (as === 'select') {
    control = (
      <select className="vmt-select" {...common}>
        {children}
      </select>
    );
  } else if (type === 'password') {
    control = (
      <div className="vmt-input-wrap">
        <input className="vmt-input" type={showPassword ? 'text' : 'password'} {...common} />
        <button
          type="button"
          className="vmt-input-action"
          onClick={() => setShowPassword((shown) => !shown)}
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? 'Hide' : 'Show'}
        </button>
      </div>
    );
  } else {
    control = <input className="vmt-input" type={type} {...common} />;
  }

  return (
    <div className={`vmt-field${error ? ' is-error' : ''} ${className}`.trim()}>
      {label && (
        <label className="vmt-label" htmlFor={fieldId}>
          {label}
        </label>
      )}
      {control}
      {help && !error && (
        <span id={`${fieldId}-help`} className="vmt-help">
          {help}
        </span>
      )}
      {error && (
        <span id={`${fieldId}-error`} className="vmt-error">
          {error}
        </span>
      )}
    </div>
  );
}
