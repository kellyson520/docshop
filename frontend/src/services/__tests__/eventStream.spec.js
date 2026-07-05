import { describe, expect, it, vi } from 'vitest'
import { buildEventStreamUrl, createEventStreamClient, parseSseFrames } from '../eventStream'

describe('eventStream', () => {
  it('builds stream URL with topics', () => {
    expect(buildEventStreamUrl(['config'])).toBe('/api/v1/events/stream?topics=config')
    expect(buildEventStreamUrl(['config', 'tracking'])).toBe('/api/v1/events/stream?topics=config%2Ctracking')
  })

  it('parses SSE frames with event id and JSON data', () => {
    const { events, rest } = parseSseFrames('event: config.updated\nid: evt-1\ndata: {"topic":"config","type":"config.updated"}\n\n')

    expect(rest).toBe('')
    expect(events).toEqual([{
      event: 'config.updated',
      id: 'evt-1',
      data: { topic: 'config', type: 'config.updated' },
    }])
  })

  it('keeps partial frame in rest buffer', () => {
    const { events, rest } = parseSseFrames('event: heartbeat\ndata: {"ok":true}')

    expect(events).toEqual([])
    expect(rest).toBe('event: heartbeat\ndata: {"ok":true}')
  })

  it('starts fetch stream with bearer token', async () => {
    let capturedOptions
    const abortError = Object.assign(new Error('aborted'), { name: 'AbortError' })
    const fetchImpl = vi.fn((_url, options) => {
      capturedOptions = options
      return Promise.reject(abortError)
    })
    const client = createEventStreamClient({
      topics: ['config'],
      fetchImpl,
      getToken: () => 'jwt-token',
      reconnect: false,
    })

    client.start()
    await Promise.resolve()
    client.stop()

    expect(fetchImpl).toHaveBeenCalledWith('/api/v1/events/stream?topics=config', expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer jwt-token' }),
    }))
    expect(capturedOptions.signal).toBeDefined()
  })
})
