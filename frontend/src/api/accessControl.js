import { get, post, put } from './client'

export function listAccessGroups() {
  return get('/access-control/groups')
}

export function getResourceAccessPolicy(resourceType, resourceId) {
  return get(`/access-control/policies/${resourceType}/${resourceId}`)
}

export function updateResourceAccessPolicy(resourceType, resourceId, data) {
  return put(`/access-control/policies/${resourceType}/${resourceId}`, data)
}

export function unlockPublicAccess(shareToken, data, config = {}) {
  return post(`/share/${shareToken}/public-access/unlock`, data, config)
}

export function heartbeatPublicAccess(shareToken, data, config = {}) {
  return post(`/share/${shareToken}/public-access/grant/heartbeat`, data, config)
}

export function releasePublicAccess(shareToken, data, config = {}) {
  return post(`/share/${shareToken}/public-access/grant/release`, data, config)
}
