import { defineStore } from 'pinia'

const STORAGE_KEYS = {
  SIDEBAR_COLLAPSED: 'ui_sidebar_collapsed',
  THEME: 'ui_theme',
  LANGUAGE: 'ui_language'
}

const THEMES = {
  LIGHT: 'light',
  DARK: 'dark'
}

const LANGUAGES = {
  ZH_CN: 'zh-CN',
  EN_US: 'en-US'
}

let systemThemeCleanup = null

function getSavedTheme() {
  const savedTheme = localStorage.getItem(STORAGE_KEYS.THEME)
  return Object.values(THEMES).includes(savedTheme) ? savedTheme : null
}

function getSystemTheme() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return THEMES.LIGHT
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? THEMES.DARK
    : THEMES.LIGHT
}

export const useUiStore = defineStore('ui', {
  state: () => ({
    sidebarCollapsed: localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED) === 'true',
    theme: getSavedTheme() || getSystemTheme(),
    followSystemTheme: !getSavedTheme(),
    language: localStorage.getItem(STORAGE_KEYS.LANGUAGE) || LANGUAGES.ZH_CN
  }),

  getters: {
    isDark: (state) => state.theme === THEMES.DARK,
    isZhCn: (state) => state.language === LANGUAGES.ZH_CN
  },

  actions: {
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
      localStorage.setItem(STORAGE_KEYS.SIDEBAR_COLLAPSED, String(this.sidebarCollapsed))
    },

    setSidebarCollapsed(collapsed) {
      this.sidebarCollapsed = collapsed
      localStorage.setItem(STORAGE_KEYS.SIDEBAR_COLLAPSED, String(collapsed))
    },

    toggleTheme() {
      this.followSystemTheme = false
      this.theme = this.theme === THEMES.LIGHT ? THEMES.DARK : THEMES.LIGHT
      this._applyTheme()
      localStorage.setItem(STORAGE_KEYS.THEME, this.theme)
    },

    setTheme(theme) {
      if (!Object.values(THEMES).includes(theme)) {
        console.warn(`[UI Store] 不支持的主题模式: ${theme}`)
        return
      }

      this.followSystemTheme = false
      this.theme = theme
      this._applyTheme()
      localStorage.setItem(STORAGE_KEYS.THEME, theme)
    },

    setLanguage(language) {
      if (!Object.values(LANGUAGES).includes(language)) {
        console.warn(`[UI Store] 不支持的语言: ${language}`)
        return
      }

      this.language = language
      localStorage.setItem(STORAGE_KEYS.LANGUAGE, language)
    },

    _applyTheme() {
      if (typeof document !== 'undefined') {
        document.documentElement.setAttribute('data-theme', this.theme)
      }
    },

    _syncThemeWithSystem(isDark) {
      if (!this.followSystemTheme) return

      this.theme = isDark ? THEMES.DARK : THEMES.LIGHT
      this._applyTheme()
    },

    _bindSystemThemeListener() {
      if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
        return
      }

      if (systemThemeCleanup) {
        systemThemeCleanup()
        systemThemeCleanup = null
      }

      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const handler = (event) => {
        this._syncThemeWithSystem(Boolean(event.matches))
      }

      if (typeof mediaQuery.addEventListener === 'function') {
        mediaQuery.addEventListener('change', handler)
        systemThemeCleanup = () => mediaQuery.removeEventListener('change', handler)
        return
      }

      if (typeof mediaQuery.addListener === 'function') {
        mediaQuery.addListener(handler)
        systemThemeCleanup = () => mediaQuery.removeListener(handler)
      }
    },

    initTheme() {
      this.followSystemTheme = !getSavedTheme()

      if (this.followSystemTheme) {
        this.theme = getSystemTheme()
      }

      this._bindSystemThemeListener()
      this._applyTheme()
    },

    reset() {
      this.sidebarCollapsed = false
      this.followSystemTheme = true
      this.theme = getSystemTheme()
      this.language = LANGUAGES.ZH_CN

      localStorage.removeItem(STORAGE_KEYS.SIDEBAR_COLLAPSED)
      localStorage.removeItem(STORAGE_KEYS.THEME)
      localStorage.removeItem(STORAGE_KEYS.LANGUAGE)

      this._applyTheme()
    }
  }
})
