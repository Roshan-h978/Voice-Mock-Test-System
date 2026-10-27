import { ATTEMPT_STATUS, TEST_STATUS, USER_STATUS } from '../utils/constants';

const MAPS = { attempt: ATTEMPT_STATUS, test: TEST_STATUS, user: USER_STATUS };

/**
 * Coloured status pill that always shows a word.
 * Use `kind` + `status` for known statuses, or `tone` + children for anything else.
 */
export default function StatusBadge({ kind, status, tone, children }) {
  const known = kind ? MAPS[kind]?.[status] : null;
  const badgeTone = tone || known?.tone || 'locked';
  return <span className={`vmt-badge vmt-badge-${badgeTone}`}>{children || known?.label || status}</span>;
}
