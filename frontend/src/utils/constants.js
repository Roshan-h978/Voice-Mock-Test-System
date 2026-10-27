// Shared values for the whole app. Labels match the backend choices.

export const APP_NAME = 'Voice Mock Test';

export const ROLES = Object.freeze({ STUDENT: 'student', ADMIN: 'admin' });

export const ROLE_HOME = Object.freeze({ student: '/student', admin: '/admin' });

/** Where to send a user after sign-in: the page they asked for (if it's in their area) or their dashboard. */
export function homeFor(user, requestedPath) {
  const home = ROLE_HOME[user?.role] || '/';
  return requestedPath && requestedPath.startsWith(home) ? requestedPath : home;
}

export const LEVELS = Object.freeze([
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
]);

// tone = the StatusBadge colour: ready (teal), progress (amber), locked (grey), danger (red), navy
export const TEST_STATUS = Object.freeze({
  draft: { label: 'Draft', tone: 'locked' },
  published: { label: 'Published', tone: 'ready' },
  archived: { label: 'Archived', tone: 'locked' },
});

export const ATTEMPT_STATUS = Object.freeze({
  in_progress: { label: 'In progress', tone: 'progress' },
  scored: { label: 'Scored', tone: 'ready' },
  needs_review: { label: 'Needs review', tone: 'progress' },
  reviewed: { label: 'Reviewed', tone: 'navy' },
});

export const USER_STATUS = Object.freeze({
  active: { label: 'Active', tone: 'ready' },
  suspended: { label: 'Suspended', tone: 'danger' },
});

export const SKILLS = Object.freeze([
  { key: 'fluency', label: 'Fluency', description: 'Pace, pauses and filler words' },
  { key: 'pronunciation', label: 'Pronunciation', description: 'How clearly your words were heard' },
  { key: 'grammar', label: 'Grammar', description: 'Accuracy and range of grammar' },
]);

export const DEFAULT_WEIGHTS = Object.freeze({ fluency: 40, pronunciation: 30, grammar: 30 });

export const STORAGE_KEYS = Object.freeze({
  access: 'vmt.accessToken',
  refresh: 'vmt.refreshToken',
});

export const SESSION_EXPIRED_EVENT = 'vmt:session-expired';

export const MIC_CHECK_SECONDS = 5;

export const PAGE_SIZE = 20;
