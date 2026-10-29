// Admin requests: dashboard, students, tests, questions, reviews and reports.

import api from './api';

// ---- Dashboard and setup -------------------------------------------------
export async function getDashboard() {
  const { data } = await api.get('/admin/dashboard/');
  return data;
}

export async function getEvaluationConfig() {
  const { data } = await api.get('/evaluation/config/');
  return data;
}

export async function checkAiConnection() {
  const { data } = await api.post('/evaluation/check/');
  return data.results;
}

export async function sendTestEmail(to) {
  const { data } = await api.post('/notifications/test-email/', to ? { to } : {});
  return data;
}

// ---- Users ---------------------------------------------------------------
/** params: { role?, status?, level?, search?, ordering?, page? } */
export async function getUsers(params = {}) {
  const { data } = await api.get('/admin/users/', { params });
  return data;
}

export async function updateUser(userId, changes) {
  const { data } = await api.patch(`/admin/users/${userId}/`, changes);
  return data;
}

/** Adds a person directly. payload: { email, full_name, role, level, phone?, password } */
export async function createUser(payload) {
  const { data } = await api.post('/admin/users/', payload);
  return data;
}

/** Deletes the account with all its results and recordings. */
export async function deleteUser(userId) {
  await api.delete(`/admin/users/${userId}/`);
}

/** payload: { email, full_name?, role } */
export async function inviteUser(payload) {
  const { data } = await api.post('/admin/users/invite/', payload);
  return data;
}

// ---- Tests ---------------------------------------------------------------
export async function getTests(params = {}) {
  const { data } = await api.get('/admin/tests/', { params });
  return data;
}

export async function getTest(testId) {
  const { data } = await api.get(`/admin/tests/${testId}/`);
  return data;
}

export async function createTest(payload) {
  const { data } = await api.post('/admin/tests/', payload);
  return data;
}

export async function updateTest(testId, changes) {
  const { data } = await api.patch(`/admin/tests/${testId}/`, changes);
  return data;
}

/** withResults: also delete the results students have for this test (otherwise the server refuses). */
export async function deleteTest(testId, { withResults = false } = {}) {
  await api.delete(`/admin/tests/${testId}/`, { params: withResults ? { with_results: 'true' } : undefined });
}

// ---- Questions -----------------------------------------------------------
export async function getQuestions(testId) {
  const { data } = await api.get('/admin/questions/', { params: { test: testId } });
  return data;
}

export async function createQuestion(payload) {
  const { data } = await api.post('/admin/questions/', payload);
  return data;
}

export async function updateQuestion(questionId, changes) {
  const { data } = await api.patch(`/admin/questions/${questionId}/`, changes);
  return data;
}

export async function deleteQuestion(questionId) {
  await api.delete(`/admin/questions/${questionId}/`);
}

/** AI-written suggestions for a test; nothing is saved. payload: { test, count, topic? } */
export async function generateQuestions(payload) {
  const { data } = await api.post('/admin/questions/generate/', payload);
  return data; // { questions: [{ text, hint }], is_demo }
}

/**
 * AI generator page: questions (and a title when with_title) from a topic; nothing is saved.
 * payload: { topic, level, count, answer_seconds, style, with_title?, test?, exclude? }
 */
export async function aiWrite(payload) {
  const { data } = await api.post('/admin/ai/write/', payload);
  return data; // { questions, is_demo, title?, description? }
}

/** Saves the AI generator's result as a new draft test. payload: { title, description, level, answer_seconds, questions } */
export async function aiCreateTest(payload) {
  const { data } = await api.post('/admin/ai/create-test/', payload);
  return data; // the new test
}

/** Adds several questions at the end of a test. questions: [{ text, hint?, answer_seconds? }] */
export async function addQuestions(testId, questions) {
  const { data } = await api.post('/admin/questions/bulk/', { test: testId, questions });
  return data; // every question of the test
}

export async function reorderQuestions(testId, orderedIds) {
  const { data } = await api.post('/admin/questions/reorder/', { test: testId, order: orderedIds });
  return data;
}

// ---- Attempts and reviews ------------------------------------------------
/** params: { status?, test?, student?, search?, date_from?, date_to?, page? } */
export async function getAttempts(params = {}) {
  const { data } = await api.get('/admin/attempts/', { params });
  return data;
}

export async function getAttempt(attemptId) {
  const { data } = await api.get(`/admin/attempts/${attemptId}/`);
  return data;
}

/** Deletes one result with its answers and recordings. */
export async function deleteAttempt(attemptId) {
  await api.delete(`/admin/attempts/${attemptId}/`);
}

/** payload: { fluency?, pronunciation?, grammar?, strengths?, tip?, next_step?, reviewer_note?, notify_student? } */
export async function reviewAttempt(attemptId, payload) {
  const { data } = await api.post(`/admin/attempts/${attemptId}/review/`, payload);
  return data; // { attempt, email_sent }
}

export async function rescoreAnswer(answerId) {
  const { data } = await api.post(`/evaluation/answers/${answerId}/rescore/`);
  return data;
}

// ---- Reports -------------------------------------------------------------
/** params: { date_from, date_to, test?, level? } */
export async function getReport(params = {}) {
  const { data } = await api.get('/admin/reports/', { params });
  return data;
}

/** Downloads the report as a CSV file in the browser. */
export async function downloadReportCsv(params = {}) {
  const response = await api.get('/admin/reports/export/', { params, responseType: 'blob' });
  const disposition = response.headers['content-disposition'] || '';
  const match = disposition.match(/filename="?([^"]+)"?/);
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = match ? match[1] : 'voice-mock-test-report.csv';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
