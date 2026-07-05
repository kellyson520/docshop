import { onBeforeUnmount, onMounted, ref, unref, watch } from 'vue'
import { createEventStreamClient } from '@/services/eventStream'

export function useEventChannel({ topics = [], onEvent, enabled = true } = {}) {
  const connected = ref(false)
  const lastEvent = ref(null)
  const error = ref(null)
  let client = null

  const start = () => {
    if (client || !unref(enabled)) return
    client = createEventStreamClient({
      topics,
      onEvent: (event) => {
        lastEvent.value = event
        onEvent?.(event)
      },
      onError: (err) => {
        error.value = err
      },
      onStateChange: (state) => {
        connected.value = state === 'open'
      },
    })
    client.start()
  }

  const stop = () => {
    client?.stop()
    client = null
    connected.value = false
  }

  const restart = () => {
    stop()
    start()
  }

  onMounted(start)
  onBeforeUnmount(stop)

  watch(() => unref(enabled), (value) => {
    if (value) start()
    else stop()
  })

  return {
    connected,
    lastEvent,
    error,
    restart,
    stop,
  }
}
