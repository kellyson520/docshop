export const ROUTE_PROGRESS_ATTR = 'data-route-progress'

let settleTimer = null

function getRoot(root) {
  if (root) return root
  if (typeof document === 'undefined') return null
  return document.documentElement || null
}

export function setRouteProgressState(state = 'idle', root) {
  const target = getRoot(root)
  target?.setAttribute(ROUTE_PROGRESS_ATTR, state)
  return state
}

export function startRouteProgress(root) {
  if (settleTimer) {
    clearTimeout(settleTimer)
    settleTimer = null
  }
  return setRouteProgressState('loading', root)
}

export function finishRouteProgress(root) {
  if (settleTimer) {
    clearTimeout(settleTimer)
  }
  setRouteProgressState('complete', root)
  settleTimer = setTimeout(() => {
    setRouteProgressState('idle', root)
    settleTimer = null
  }, 180)
}

export function resetRouteProgress(root) {
  if (settleTimer) {
    clearTimeout(settleTimer)
    settleTimer = null
  }
  return setRouteProgressState('idle', root)
}
