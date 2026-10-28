import { Link } from 'react-router-dom';

/**
 * Design-system button. Renders a <Link> when `to` is set, an <a> for `href`,
 * otherwise a <button>.
 *
 * variant: primary | secondary | ghost | danger | on-navy
 * size: md | sm
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  block = false,
  loading = false,
  icon: Icon,
  iconRight: IconRight,
  to,
  href,
  type = 'button',
  disabled = false,
  className = '',
  children,
  ...rest
}) {
  const classes = [
    'vmt-btn',
    `vmt-btn-${variant}`,
    size === 'sm' && 'vmt-btn-sm',
    block && 'vmt-btn-block',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const content = (
    <>
      {loading ? (
        <span className="vmt-spinner vmt-spinner-sm" aria-hidden="true" />
      ) : (
        Icon && <Icon className="vmt-icon" aria-hidden="true" />
      )}
      {children !== undefined && children !== null && <span>{children}</span>}
      {IconRight && !loading && <IconRight className="vmt-icon vmt-btn-icon-right" aria-hidden="true" />}
    </>
  );

  if (to) {
    return (
      <Link to={to} className={classes} {...rest}>
        {content}
      </Link>
    );
  }
  if (href) {
    return (
      <a href={href} className={classes} {...rest}>
        {content}
      </a>
    );
  }
  return (
    <button type={type} className={classes} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {content}
    </button>
  );
}
