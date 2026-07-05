/**
 * 差异对比相关 API
 * 使用封装的 get 方法
 */

import { get } from './client'

export function getDiffs(fileId, params) {
  return get(`/files/${fileId}/diffs`, params)
}

export function getDiff(fileId, diffId) {
  return get(`/files/${fileId}/diffs/${diffId}`)
}
