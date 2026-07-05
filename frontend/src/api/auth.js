import { post, get } from './client'

/**
 * 用户登录
 * @param {string} username - 用户名
 * @param {string} password - 密码
 * @returns {Promise<{access_token: string}>}
 */
export function login(username, password) {
  return post('/auth/login', { username, password })
}

/**
 * 用户注册
 * @param {string} username - 用户名
 * @param {string} password - 密码
 * @returns {Promise<Object>}
 */
export function register(username, password) {
  return post('/auth/register', { username, password })
}

export function getRegistrationPolicy() {
  return get('/auth/registration-policy')
}

/**
 * 获取当前登录用户信息
 * @returns {Promise<Object>}
 */
export function getMe() {
  return get('/auth/me')
}
