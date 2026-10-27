// A student's results, history and progress numbers.

import api from './api';

/** params: { status?: 'finished' | 'in_progress' | ..., test?, page?, page_size? } */
export async function getMyAttempts(params = {}) {
  const { data } = await api.get('/attempts/', { params });
  return data; // { count, next, previous, results }
}

export async function getResult(attemptId) {
  const { data } = await api.get(`/attempts/${attemptId}/`);
  return data;
}

export async function getMyStats() {
  const { data } = await api.get('/me/stats/');
  return data;
}
