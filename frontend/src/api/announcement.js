import { del, get, post, put } from './client'

export function listAnnouncements(params) {
  return get('/announcements', params)
}

export function listActiveAnnouncements() {
  return get('/announcements/active')
}

export function createAnnouncement(payload) {
  return post('/announcements', payload)
}

export function updateAnnouncement(id, payload) {
  return put(`/announcements/${id}`, payload)
}

export function deleteAnnouncement(id) {
  return del(`/announcements/${id}`)
}
