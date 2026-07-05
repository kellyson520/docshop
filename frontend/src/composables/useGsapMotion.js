import { onBeforeUnmount } from 'vue'

let gsapLoader

function getAppMotionMode() {
  if (typeof document === 'undefined' && typeof window === 'undefined') return 'system'

  const rootMode = typeof document !== 'undefined'
    ? document.documentElement?.getAttribute('data-motion-mode')
    : null

  if (rootMode) return String(rootMode).toLowerCase()

  try {
    return String(window?.localStorage?.getItem('docshop_motion_mode') || 'system').toLowerCase()
  } catch {
    return 'system'
  }
}

export function shouldReduceMotion() {
  const appMotionMode = getAppMotionMode()
  if (appMotionMode === 'off' || appMotionMode === 'reduced') return true

  try {
    return typeof window !== 'undefined'
      && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  } catch {
    return false
  }
}

async function loadGsap() {
  if (!gsapLoader) {
    gsapLoader = (async () => await import('gsap'))()
  }
  const mod = await gsapLoader
  return mod.gsap || mod.default
}

export function useGsapScoped(rootRef) {
  let ctx

  function revertGsap() {
    ctx?.revert()
    ctx = null
  }

  async function runGsap(setup) {
    if (!rootRef?.value || shouldReduceMotion()) return null

    const gsap = await loadGsap()
    if (!rootRef?.value) return null

    revertGsap()
    ctx = gsap.context(() => setup(gsap, rootRef.value), rootRef.value)
    return ctx
  }

  onBeforeUnmount(() => {
    revertGsap()
  })

  return {
    runGsap,
    revertGsap,
    shouldReduceMotion
  }
}
