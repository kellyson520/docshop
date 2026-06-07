/**
 * 全局 UI 状态管理
 * 管理侧边栏折叠状态、主题模式、语言偏好
 * 使用 localStorage 进行持久化
 */

import { defineStore } from 'pinia'

/**
 * localStorage 存储键名
 */
const STORAGE_KEYS = {
  SIDEBAR_COLLAPSED: 'ui_sidebar_collapsed',
  THEME: 'ui_theme',
  LANGUAGE: 'ui_language'
}

/**
 * 支持的主题模式
 */
const THEMES = {
  LIGHT: 'light',
  DARK: 'dark'
}

/**
 * 支持的语言
 */
const LANGUAGES = {
  ZH_CN: 'zh-CN',
  EN_US: 'en-US'
}

export const useUiStore = defineStore('ui', {
  state: () => ({
    // 侧边栏是否折叠
    sidebarCollapsed: localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED) === 'true',
    // 主题模式：light 或 dark
    theme: localStorage.getItem(STORAGE_KEYS.THEME) || THEMES.LIGHT,
    // 语言偏好
    language: localStorage.getItem(STORAGE_KEYS.LANGUAGE) || LANGUAGES.ZH_CN
  }),

  getters: {
    /** 是否为暗色模式 */
    isDark: (state) => state.theme === THEMES.DARK,

    /** 是否为中文 */
    isZhCn: (state) => state.language === LANGUAGES.ZH_CN
  },

  actions: {
    /**
     * 切换侧边栏折叠状态
     */
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
      localStorage.setItem(STORAGE_KEYS.SIDEBAR_COLLAPSED, String(this.sidebarCollapsed))
    },

    /**
     * 设置侧边栏折叠状态
     * @param {boolean} collapsed - 是否折叠
     */
    setSidebarCollapsed(collapsed) {
      this.sidebarCollapsed = collapsed
      localStorage.setItem(STORAGE_KEYS.SIDEBAR_COLLAPSED, String(collapsed))
    },

    /**
     * 切换主题模式（light <-> dark）
     */
    toggleTheme() {
      this.theme = this.theme === THEMES.LIGHT ? THEMES.DARK : THEMES.LIGHT
      this._applyTheme()
      localStorage.setItem(STORAGE_KEYS.THEME, this.theme)
    },

    /**
     * 设置主题模式
     * @param {string} theme - 主题模式（light/dark）
     */
    setTheme(theme) {
      if (!Object.values(THEMES).includes(theme)) {
        console.warn(`[UI Store] 不支持的主题模式: ${theme}`)
        return
      }
      this.theme = theme
      this._applyTheme()
      localStorage.setItem(STORAGE_KEYS.THEME, theme)
    },

    /**
     * 设置语言
     * @param {string} language - 语言代码
     */
    setLanguage(language) {
      if (!Object.values(LANGUAGES).includes(language)) {
        console.warn(`[UI Store] 不支持的语言: ${language}`)
        return
      }
      this.language = language
      localStorage.setItem(STORAGE_KEYS.LANGUAGE, language)
    },

    /**
     * 将主题应用到 document 根元素
     * @private
     */
    _applyTheme() {
      if (typeof document !== 'undefined') {
        document.documentElement.setAttribute('data-theme', this.theme)
      }
    },

    /**
     * 初始化主题（应用已持久化的主题）
     */
    initTheme() {
      this._applyTheme()
    },

    /**
     * 重置 UI 状态为默认值
     */
    reset() {
      this.sidebarCollapsed = false
      this.theme = THEMES.LIGHT
      this.language = LANGUAGES.ZH_CN
      localStorage.removeItem(STORAGE_KEYS.SIDEBAR_COLLAPSED)
      localStorage.removeItem(STORAGE_KEYS.THEME)
      localStorage.removeItem(STORAGE_KEYS.LANGUAGE)
      this._applyTheme()
    }
  }
})
