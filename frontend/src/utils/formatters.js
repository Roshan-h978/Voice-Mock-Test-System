// Small display helpers used across pages.

import { DEFAULT_WEIGHTS, LEVELS } from './constants';

const dateFormat = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
const dateTimeFormat = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

function toDate(value) {
  if (!value) return null;
  // A plain day ("2026-10-24") is read as local time. new Date() would read it as midnight UTC,
  // which shows the day before in time zones behind UTC.
  const dayOnly = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
  const date = value instanceof Date ? value : new Date(dayOnly ? `${value}T00:00:00` : value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** 24 Oct 2026 */
export function formatDate(value) {
  const date = toDate(value);
  return date ? dateFormat.format(date) : '—';
}

/** 24 Oct 2026, 9:45 pm */
export function formatDateTime(value) {
  const date = toDate(value);
  return date ? dateTimeFormat.format(date) : '—';
}

/** YYYY-MM-DD for <input type="date"> */
export function toInputDate(date) {
  const d = toDate(date) || new Date();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${month}-${day}`;
}

/** 65 -> "1:05" */
export function formatDuration(totalSeconds) {
  const seconds = Math.max(0, Math.round(Number(totalSeconds) || 0));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}

/** 78 -> "78%", null -> "—" */
export function formatScore(value) {
  return value === null || value === undefined ? '—' : `${Math.round(value)}%`;
}

/** +12% / -5% / no change */
export function formatChange(percent, suffix = 'vs last week') {
  if (percent === null || percent === undefined) return '';
  if (percent === 0) return `No change ${suffix}`;
  return `${percent > 0 ? '+' : ''}${percent}% ${suffix}`;
}

export function initials(name = '') {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '?';
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
}

export function firstName(name = '') {
  return name.trim().split(/\s+/)[0] || '';
}

export function levelLabel(value) {
  return LEVELS.find((level) => level.value === value)?.label || '—';
}

export function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

export function skillLabel(key) {
  return key ? key.charAt(0).toUpperCase() + key.slice(1) : '—';
}

/** Same rule as the backend: weighted average of the three skills. */
export function overallFromSkills(skills, weights = DEFAULT_WEIGHTS) {
  let total = 0;
  let weightSum = 0;
  Object.entries(weights).forEach(([key, weight]) => {
    const value = Number(skills[key]);
    if (skills[key] !== '' && skills[key] !== null && !Number.isNaN(value) && weight) {
      total += value * weight;
      weightSum += weight;
    }
  });
  return weightSum ? Math.round(total / weightSum) : null;
}

export function headlineFor(score) {
  if (score === null || score === undefined) return '';
  if (score >= 80) return 'Great job!';
  if (score >= 60) return 'Good progress';
  return 'Keep practising';
}

/** "just now", "5 min ago", "3 hours ago", "yesterday", "4 days ago", then the date */
export function timeAgo(value) {
  const date = toDate(value);
  if (!date) return '—';
  const minutes = Math.round((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return hours === 1 ? '1 hour ago' : `${hours} hours ago`;
  const days = Math.round(hours / 24);
  if (days === 1) return 'yesterday';
  if (days < 7) return `${days} days ago`;
  return formatDate(date);
}
