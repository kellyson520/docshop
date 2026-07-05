const DEFAULT_APP_NAME = 'DocShop'
const DEFAULT_SEPARATOR = ' - '

function normalizeTitle(value) {
  if (typeof value !== 'string') return ''
  return value.trim()
}

function getDeepestMatchedTitle(route) {
  const matched = Array.isArray(route?.matched) ? route.matched : []
  for (let index = matched.length - 1; index >= 0; index -= 1) {
    const title = normalizeTitle(matched[index]?.meta?.title)
    if (title) return title
  }
  return ''
}

export function resolveDocumentTitle(route, options = {}) {
  const appName = normalizeTitle(options.appName) || DEFAULT_APP_NAME
  const separator = typeof options.separator === 'string' ? options.separator : DEFAULT_SEPARATOR
  const directTitle = normalizeTitle(route?.meta?.title)
  const routeTitle = directTitle || getDeepestMatchedTitle(route)

  if (!routeTitle || routeTitle === appName || routeTitle === '首页') {
    return appName
  }

  return `${routeTitle}${separator}${appName}`
}

export function setDocumentTitle(route, options = {}) {
  const title = resolveDocumentTitle(route, options)

  if (typeof document !== 'undefined') {
    document.title = title
  }

  return title
}
