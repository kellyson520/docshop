import { describe, expect, it, vi } from 'vitest'
import {
  describeBatchResult,
  getBatchFailureMessage,
  runBatchOperation
} from '../batchOperation.js'

describe('batchOperation utilities', () => {
  it('runs every item and keeps going after item failures by default', async () => {
    const seen = []
    const result = await runBatchOperation([1, 2, 3], async (item) => {
      seen.push(item)
      if (item === 2) throw new Error('项目 2 更新失败')
      return item * 10
    })

    expect(seen).toEqual([1, 2, 3])
    expect(result.total).toBe(3)
    expect(result.successCount).toBe(2)
    expect(result.failureCount).toBe(1)
    expect(result.ok).toBe(false)
    expect(result.partial).toBe(true)
    expect(result.successes.map((entry) => entry.result)).toEqual([10, 30])
    expect(result.failures[0].item).toBe(2)
  })

  it('can stop on the first failure when requested', async () => {
    const seen = []
    const result = await runBatchOperation([1, 2, 3], async (item) => {
      seen.push(item)
      if (item === 2) throw new Error('stop')
      return item
    }, { continueOnError: false })

    expect(seen).toEqual([1, 2])
    expect(result.successCount).toBe(1)
    expect(result.failureCount).toBe(1)
    expect(result.skippedCount).toBe(1)
  })

  it('reports deterministic progress from 0 to 100', async () => {
    const onProgress = vi.fn()

    await runBatchOperation(['a', 'b'], async (item) => item, { onProgress })

    expect(onProgress.mock.calls.map(([event]) => event.percent)).toEqual([0, 50, 100])
    expect(onProgress.mock.calls.at(-1)[0]).toMatchObject({
      processed: 2,
      total: 2,
      successCount: 2,
      failureCount: 0
    })
  })

  it('formats full, partial and failed summaries for user feedback', () => {
    expect(describeBatchResult({ total: 3, successCount: 3, failureCount: 0 }, {
      successVerb: '已公开',
      unit: '个项目'
    })).toEqual({ type: 'success', message: '已公开 3 个项目' })

    expect(describeBatchResult({ total: 3, successCount: 2, failureCount: 1 }, {
      successVerb: '已公开',
      failureVerb: '公开失败',
      unit: '个项目'
    })).toEqual({ type: 'warning', message: '已公开 2/3 个项目，1 个项目公开失败' })

    expect(describeBatchResult({ total: 3, successCount: 0, failureCount: 3 }, {
      failureVerb: '公开失败',
      unit: '个项目'
    })).toEqual({ type: 'error', message: '3 个项目公开失败' })
  })

  it('extracts a useful first failure message', () => {
    const result = {
      failures: [
        { item: 7, error: { response: { data: { message: '没有权限' } } } }
      ]
    }

    expect(getBatchFailureMessage(result, '批量设置失败')).toBe('项目 7：没有权限')
  })
})
