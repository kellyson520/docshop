/**
 * Token 有效性检查组合式函数
 * 解析 JWT payload 检查 exp 时间戳，判断 token 是否过期
 */

/**
 * 解析 JWT Token 的 payload 部分
 * @param {string} token - JWT Token 字符串
 * @returns {Object|null} 解析后的 payload 对象，解析失败返回 null
 */
function parseJwtPayload(token) {
  if (!token || typeof token !== 'string') return null

  try {
    // JWT 由三部分组成：header.payload.signature
    const parts = token.split('.')
    if (parts.length !== 3) return null

    // payload 是 Base64Url 编码的
    const base64Url = parts[1]
    // 将 Base64Url 转换为标准 Base64
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    // 解码
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch {
    return null
  }
}

/**
 * 检查 Token 是否有效（未过期）
 * @param {string} [token] - JWT Token 字符串，不传则从 localStorage 读取
 * @param {number} [bufferSeconds=60] - 提前多少秒判定为过期（缓冲时间），默认 60 秒
 * @returns {boolean} token 是否有效
 */
export function isTokenValid(token, bufferSeconds = 60) {
  // 如果未传入 token，从 localStorage 读取
  if (!token) {
    token = localStorage.getItem('access_token')
  }

  if (!token) return false

  const payload = parseJwtPayload(token)
  if (!payload || !payload.exp) return false

  // exp 是秒级时间戳，转换为毫秒
  const expTimeMs = payload.exp * 1000
  const now = Date.now()

  // 加上缓冲时间，提前判定过期
  return now < expTimeMs - bufferSeconds * 1000
}

/**
 * 获取 Token 的过期时间
 * @param {string} [token] - JWT Token 字符串
 * @returns {Date|null} 过期时间 Date 对象，无法解析返回 null
 */
export function getTokenExpireTime(token) {
  if (!token) {
    token = localStorage.getItem('access_token')
  }

  if (!token) return null

  const payload = parseJwtPayload(token)
  if (!payload || !payload.exp) return null

  return new Date(payload.exp * 1000)
}

/**
 * 获取 Token 的剩余有效时间（毫秒）
 * @param {string} [token] - JWT Token 字符串
 * @returns {number} 剩余有效毫秒数，已过期返回 0，无法解析返回 -1
 */
export function getTokenRemainingTime(token) {
  if (!token) {
    token = localStorage.getItem('access_token')
  }

  if (!token) return -1

  const payload = parseJwtPayload(token)
  if (!payload || !payload.exp) return -1

  const expTimeMs = payload.exp * 1000
  const remaining = expTimeMs - Date.now()

  return remaining > 0 ? remaining : 0
}

/**
 * Token 检查组合式函数
 * @returns {Object} token 检查相关方法
 */
export function useTokenCheck() {
  return {
    isTokenValid,
    getTokenExpireTime,
    getTokenRemainingTime,
    parseJwtPayload
  }
}

export default useTokenCheck
