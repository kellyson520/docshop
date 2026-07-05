function getMotionMode() {
  if (typeof document !== 'undefined') {
    const rootMode = document.documentElement?.getAttribute('data-motion-mode')
    if (rootMode) return String(rootMode).toLowerCase()
  }

  try {
    return String(window?.localStorage?.getItem('docshop_motion_mode') || 'system').toLowerCase()
  } catch {
    return 'system'
  }
}

export function shouldUseInstantScroll() {
  const mode = getMotionMode()
  if (mode === 'off' || mode === 'reduced') return true

  try {
    return Boolean(window?.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches)
  } catch {
    return false
  }
}

export function getRouteScrollBehavior() {
  return shouldUseInstantScroll() ? 'auto' : 'smooth'
}

export function resolveRouteScrollPosition(to = {}, from = {}, savedPosition = null) {
  if (savedPosition) return savedPosition

  const behavior = getRouteScrollBehavior()

  if (to?.hash) {
    return {
      el: to.hash,
      behavior
    }
  }

  return {
    left: 0,
    top: 0,
    behavior
  }
}
