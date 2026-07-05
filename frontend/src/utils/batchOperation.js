function toArray(items) {
  if (!items) return []
  return Array.isArray(items) ? [...items] : Array.from(items)
}

function clampPercent(value) {
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(100, Math.round(value)))
}

function getErrorMessage(error, fallback = '操作失败') {
  const data = error?.response?.data ?? error?.data ?? error?.body
  return (
    data?.message ||
    data?.detail ||
    error?.message ||
    fallback
  )
}

function createProgressEvent({ processed, total, successCount, failureCount, item = null, index = -1 }) {
  return {
    processed,
    total,
    percent: total > 0 ? clampPercent((processed / total) * 100) : 100,
    successCount,
    failureCount,
    item,
    index
  }
}

export async function runBatchOperation(items, worker, options = {}) {
  const list = toArray(items)
  const { continueOnError = true, onProgress, onItemError } = options
  const successes = []
  const failures = []

  onProgress?.(createProgressEvent({
    processed: 0,
    total: list.length,
    successCount: 0,
    failureCount: 0
  }))

  for (let index = 0; index < list.length; index += 1) {
    const item = list[index]
    try {
      const result = await worker(item, index)
      successes.push({ item, index, result })
    } catch (error) {
      const failure = { item, index, error }
      failures.push(failure)
      onItemError?.(failure)
      if (!continueOnError) {
        onProgress?.(createProgressEvent({
          processed: index + 1,
          total: list.length,
          successCount: successes.length,
          failureCount: failures.length,
          item,
          index
        }))
        break
      }
    }

    onProgress?.(createProgressEvent({
      processed: index + 1,
      total: list.length,
      successCount: successes.length,
      failureCount: failures.length,
      item,
      index
    }))
  }

  return {
    total: list.length,
    successCount: successes.length,
    failureCount: failures.length,
    skippedCount: Math.max(0, list.length - successes.length - failures.length),
    successes,
    failures,
    ok: failures.length === 0,
    partial: successes.length > 0 && failures.length > 0
  }
}

export function describeBatchResult(result, options = {}) {
  const {
    successVerb = '已处理',
    failureVerb = '处理失败',
    unit = '项'
  } = options

  const total = Number(result?.total || 0)
  const successCount = Number(result?.successCount || 0)
  const failureCount = Number(result?.failureCount || 0)

  if (total <= 0) {
    return { type: 'info', message: `没有可${successVerb.replace(/^已/, '')}的${unit}` }
  }

  if (failureCount === 0) {
    return { type: 'success', message: `${successVerb} ${successCount} ${unit}` }
  }

  if (successCount === 0) {
    return { type: 'error', message: `${failureCount} ${unit}${failureVerb}` }
  }

  return {
    type: 'warning',
    message: `${successVerb} ${successCount}/${total} ${unit}，${failureCount} ${unit}${failureVerb}`
  }
}

export function getBatchFailureMessage(result, fallback = '批量操作失败') {
  const firstFailure = result?.failures?.[0]
  if (!firstFailure) return fallback

  const message = getErrorMessage(firstFailure.error, fallback)
  const itemLabel = firstFailure.item?.name || firstFailure.item?.title || firstFailure.item
  return itemLabel !== undefined && itemLabel !== null
    ? `项目 ${itemLabel}：${message}`
    : message
}

export default {
  runBatchOperation,
  describeBatchResult,
  getBatchFailureMessage
}
