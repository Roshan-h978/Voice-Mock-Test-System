// In-app notifications (the bell in the top bar).

import api from './api';

/** params: { unread?: 1, page?, page_size? } */
export async function getNotifications(params = {}) {
  const { data } = await api.get('/notifications/', { params });
  return data; // { count, results, page, pages, next, previous }
}

export async function getUnreadCount() {
  const { data } = await api.get('/notifications/unread-count/');
  return data.count;
}

export async function markRead(id) {
  const { data } = await api.post(`/notifications/${id}/read/`);
  return data;
}

export async function markAllRead() {
  const { data } = await api.post('/notifications/read-all/');
  return data;
}
