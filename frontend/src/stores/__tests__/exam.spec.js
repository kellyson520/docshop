import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useExamStore } from '../exam.js'

const { mockGetUpcomingExams } = vi.hoisted(() => ({
  mockGetUpcomingExams: vi.fn()
}))

vi.mock('@/api/exam', () => ({
  getExams: vi.fn(),
  getExam: vi.fn(),
  createExam: vi.fn(),
  updateExam: vi.fn(),
  deleteExam: vi.fn(),
  getUpcomingExams: (...args) => mockGetUpcomingExams(...args),
  dismissReminder: vi.fn()
}))

describe('exam store reminder checks', () => {
  let consoleErrorSpy

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    consoleErrorSpy?.mockRestore()
  })

  it('propagates upcoming/start exam check failures so callers can show feedback', async () => {
    const store = useExamStore()
    store.upcomingReminders = [{ id: 1, reminderType: 'start' }]
    const error = new Error('start check failed')
    mockGetUpcomingExams.mockRejectedValueOnce(error)

    await expect(store.checkUpcomingExams()).rejects.toThrow('start check failed')

    expect(store.upcomingReminders).toEqual([])
    expect(store.reminderChecked).toBe(false)
  })
})
