import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

/** Page title with an optional back link, subtitle and actions on the right. */
export default function PageHeader({ title, subtitle, back, actions, overline }) {
  return (
    <div className="vmt-stack vmt-stack-sm">
      {back && (
        <Link to={back.to} className="vmt-crumb">
          <ArrowLeft className="vmt-icon-sm" aria-hidden="true" />
          {back.label}
        </Link>
      )}
      <div className="vmt-page-head">
        <div className="vmt-page-head-text">
          {overline && <span className="overline vmt-teal">{overline}</span>}
          <h1 className="title-lg">{title}</h1>
          {subtitle && <p className="body-sm vmt-muted">{subtitle}</p>}
        </div>
        {actions && <div className="vmt-row vmt-row-tight">{actions}</div>}
      </div>
    </div>
  );
}
