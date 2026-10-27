import { Mic } from 'lucide-react';
import { Link } from 'react-router-dom';
import { APP_NAME } from '../utils/constants';

/** Logo mark + product name. `subtitle` shows a small line under the name (e.g. the role). */
export default function Brand({ to = '/', subtitle }) {
  return (
    <Link to={to} className="vmt-brand" aria-label={`${APP_NAME} home`}>
      <span className="vmt-brand-mark" aria-hidden="true">
        <Mic className="vmt-icon" />
      </span>
      <span className="vmt-brand-text">
        <span>{APP_NAME}</span>
        {subtitle && <span className="vmt-role">{subtitle}</span>}
      </span>
    </Link>
  );
}
