// Quick practice, the Mistakes notebook and My progress.

import api from './api';

const EXTENSIONS = { 'audio/webm': 'webm', 'audio/ogg': 'ogg', 'audio/mp4': 'm4a', 'audio/mpeg': 'mp3', 'audio/wav': 'wav' };

function fileNameFor(mimeType = '') {
  return `practice.${EXTENSIONS[mimeType.split(';')[0].trim()] || 'webm'}`;
}

// ---- Quick practice ------------------------------------------------------
export async function getPracticeTopics() {
  const { data } = await api.get('/practice/topics/');
  return data; // [{ value, label }]
}

/** source: 'ai' (written for the topic) | 'tests' (from published tests). Nothing is saved yet. */
export async function getPracticeQuestion({ source = 'ai', topic = '' } = {}) {
  const { data } = await api.post('/practice/question/', { source, topic });
  return data; // { source, topic, topic_label, question_text, hint, time_limit, is_demo }
}

/** Uploads the recording with its question and returns the scored practice answer. */
export async function submitPracticeAnswer({ question, blob, durationSeconds }) {
  const form = new FormData();
  form.append('audio', blob, fileNameFor(blob.type));
  form.append('question_text', question.question_text);
  form.append('hint', question.hint || '');
  form.append('topic', question.topic || '');
  form.append('source', question.source || 'ai');
  form.append('time_limit', String(question.time_limit || 60));
  if (durationSeconds) form.append('duration_seconds', String(Math.round(durationSeconds * 10) / 10));
  const { data } = await api.post('/practice/answers/', form);
  return data;
}

export async function getPracticeHistory(params = {}) {
  const { data } = await api.get('/practice/answers/', { params });
  return data; // { count, results, ... }
}

export async function getPracticeAnswer(id) {
  const { data } = await api.get(`/practice/answers/${id}/`);
  return data;
}

export async function deletePracticeAnswer(id) {
  await api.delete(`/practice/answers/${id}/`);
}

// ---- Mistakes notebook ---------------------------------------------------
/** show: 'to_learn' | 'learned' | 'all' */
export async function getNotebook(show = 'to_learn') {
  const { data } = await api.get('/me/notebook/', { params: { show } });
  return data; // { corrections, tips, totals }
}

export async function setLearned(key, learned) {
  const { data } = await api.post('/me/notebook/learned/', { key, learned });
  return data;
}

// ---- My progress -----------------------------------------------------------
/** days: 30 | 90 | 365 | 0 (all time) */
export async function getProgress(days = 90) {
  const { data } = await api.get('/me/progress/', { params: { days } });
  return data;
}
