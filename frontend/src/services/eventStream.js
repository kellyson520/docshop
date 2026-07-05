const DEFAULT_RETRY_DELAY_MS = 1000
const MAX_RETRY_DELAY_MS = 10000

export function buildEventStreamUrl(topics = []) {
  const normalizedTopics = Array.from(new Set((Array.isArray(topics) ? topics : [topics]).filter(Boolean)))
  const query = new URLSearchParams()
  if (normalizedTopics.length > 0) {
    query.set('topics', normalizedTopics.join(','))
  }
  const serialized = query.toString()
  return `/api/v1/events/stream${serialized ? `?${serialized}` : ''}`
}

export function parseSseFrames(buffer = '') {
  const normalized = String(buffer || '').replace(/\r\n/g, '\n')
  const chunks = normalized.split('\n\n')
  const rest = normalized.endsWith('\n\n') ? '' : chunks.pop() || ''
  const events = []

  for (const chunk of chunks) {
    if (!chunk.trim()) continue
    const event = { event: 'message', id: '', data: '' }
    for (const rawLine of chunk.split('\n')) {
      const line = rawLine.trimEnd()
      if (!line || line.startsWith(':')) continue
      const separator = line.indexOf(':')
      const field = separator === -1 ? line : line.slice(0, separator)
      const value = separator === -1 ? '' : line.slice(separator + 1).replace(/^ /, '')
      if (field === 'event') event.event = value || 'message'
      else if (field === 'id') event.id = value
      else if (field === 'data') event.data = event.data ? `${event.data}\n${value}` : value
    }

    let payload = event.data
    if (typeof payload === 'string' && payload.length > 0) {
      try {
        payload = JSON.parse(payload)
      } catch {
        payload = event.data
      }
    }

    events.push({
      event: event.event,
      id: event.id,
      data: payload,
    })
  }

  return { events, rest }
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export function createEventStreamClient({
  topics = [],
  fetchImpl = fetch,
  getToken = () => localStorage.getItem('access_token'),
  onEvent,
  onError,
  onStateChange,
  reconnect = true,
  retryDelayMs = DEFAULT_RETRY_DELAY_MS,
  maxRetryDelayMs = MAX_RETRY_DELAY_MS,
} = {}) {
  let controller = null
  let stopped = true
  let attempt = 0
  let startPromise = null

  const emitState = (state) => {
    onStateChange?.(state)
  }

  const connect = async () => {
    while (!stopped) {
      controller = new AbortController()
      try {
        emitState('connecting')
        const headers = { Accept: 'text/event-stream' }
        const token = getToken?.()
        if (token) headers.Authorization = `Bearer ${token}`

        const response = await fetchImpl(buildEventStreamUrl(topics), {
          method: 'GET',
          headers,
          signal: controller.signal,
          cache: 'no-store',
          credentials: 'same-origin',
        })

        if (!response?.ok || !response.body) {
          const error = new Error(`Event stream request failed: ${response?.status || 'unknown'}`)
          error.status = response?.status
          throw error
        }

        attempt = 0
        emitState('open')
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (!stopped) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const parsed = parseSseFrames(buffer)
          buffer = parsed.rest
          for (const item of parsed.events) {
            if (item.event === 'heartbeat') continue
            onEvent?.(item)
          }
        }
      } catch (error) {
        if (stopped || error?.name === 'AbortError') {
          emitState('closed')
          return
        }
        onError?.(error)
        emitState('error')
        if (!reconnect || error?.status === 401 || error?.status === 403) {
          return
        }
        const delay = Math.min(retryDelayMs * (2 ** attempt), maxRetryDelayMs)
        attempt += 1
        await wait(delay)
        continue
      }

      if (!reconnect || stopped) {
        emitState('closed')
        return
      }

      emitState('reconnecting')
      const delay = Math.min(retryDelayMs * (2 ** attempt), maxRetryDelayMs)
      attempt += 1
      await wait(delay)
    }
    emitState('closed')
  }

  return {
    start() {
      if (!stopped) return startPromise
      stopped = false
      startPromise = connect()
      return startPromise
    },
    stop() {
      stopped = true
      controller?.abort()
    },
  }
}
