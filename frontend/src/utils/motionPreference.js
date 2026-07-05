export const MOTION_STORAGE_KEY = 'docshop_motion_mode'

const VALID_MOTION_MODES = new Set(['system', 'reduced', 'off'])

function getSafeStorage(storage) {
  if (storage) return storage
  if (typeof window === 'undefined') return null
  return window.localStorage || null
}

function getSafeRoot(root) {
  if (root) return root
  if (typeof document === 'undefined') return null
  return document.documentElement || null
}

export function normalizeMotionMode(mode = 'system') {
  const normalized = String(mode || 'system').trim().toLowerCase()
  return VALID_MOTION_MODES.has(normalized) ? normalized : 'system'
}

export function getStoredMotionMode(storage) {
  try {
    const safeStorage = getSafeStorage(storage)
    return normalizeMotionMode(safeStorage?.getItem(MOTION_STORAGE_KEY))
  } catch {
    return 'system'
  }
}

export function applyMotionPreference(mode = 'system', options = {}) {
  const normalized = normalizeMotionMode(mode)
  const root = getSafeRoot(options.root)
  const storage = getSafeStorage(options.storage)

  root?.setAttribute('data-motion-mode', normalized)

  try {
    storage?.setItem(MOTION_STORAGE_KEY, normalized)
  } catch {
    // Ignore private-mode/localStorage failures; DOM attribute still applies.
  }

  return normalized
}

export function initMotionPreference(options = {}) {
  return applyMotionPreference(getStoredMotionMode(options.storage), options)
}

export function bindMotionPreferenceSync(options = {}) {
  const target = options.target || (typeof window !== 'undefined' ? window : null)
  if (!target?.addEventListener) return () => {}

  const handleStorage = (event) => {
    if (event.key !== MOTION_STORAGE_KEY) return
    applyMotionPreference(event.newValue, {
      root: options.root,
      storage: options.storage
    })
  }

  target.addEventListener('storage', handleStorage)

  return () => {
    target.removeEventListener('storage', handleStorage)
  }
}
