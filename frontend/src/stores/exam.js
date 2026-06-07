import { defineStore } from 'pinia'
import {
  getExams,
  getExam,
  createExam as apiCreateExam,
  updateExam as apiUpdateExam,
  deleteExam as apiDeleteExam,
  getUpcomingExams as apiGetUpcomingExams,
  dismissReminder as apiDismissReminder
} from '@/api/exam'

/**
 * 考试状态管理 Store
 * 管理考试列表、当前考试、提醒状态等
 */
export const useExamStore = defineStore('exam', {
  state: () => ({
    // 考试列表
    exams: [],
    // 当前查看的考试详情
    currentExam: null,
    // 即将开始的考试提醒列表
    upcomingReminders: [],
    // 加载状态
    loading: false,
    // 是否已检查过提醒（防止重复弹窗）
    reminderChecked: false,
    // 已关闭的提醒记录 { examId: { '15min': true, '5min': true, 'start': true } }
    dismissedReminders: {}
  }),

  getters: {
    /**
     * 即将开始的考试（未开始）
     */
    upcomingExams: (state) => {
      const now = new Date()
      return state.exams.filter(exam => new Date(exam.start_time) > now)
    },

    /**
     * 进行中的考试
     */
    ongoingExams: (state) => {
      const now = new Date()
      return state.exams.filter(exam => {
        const startTime = new Date(exam.start_time)
        const endTime = new Date(exam.end_time)
        return startTime <= now && endTime > now
      })
    },

    /**
     * 已结束的考试
     */
    expiredExams: (state) => {
      const now = new Date()
      return state.exams.filter(exam => new Date(exam.end_time) <= now)
    },

    /**
     * 是否有待处理的提醒
     */
    hasPendingReminders: (state) => {
      return state.upcomingReminders.length > 0
    },

    /**
     * 获取考试状态
     * @returns {Function} 返回考试状态的函数
     */
    getExamStatus: () => (exam) => {
      const now = new Date()
      const startTime = new Date(exam.start_time)
      const endTime = new Date(exam.end_time)

      if (endTime <= now) {
        return 'expired'
      } else if (startTime <= now) {
        return 'ongoing'
      } else {
        // 15分钟内即将开始
        const diffMinutes = (startTime - now) / (1000 * 60)
        if (diffMinutes <= 15) {
          return 'soon'
        }
        return 'upcoming'
      }
    }
  },

  actions: {
    /**
     * 获取考试列表
     * @param {Object} params - 查询参数
     */
    async fetchExams(params = {}) {
      this.loading = true
      try {
        const data = await getExams(params)
        this.exams = data.items || data || []
        return data
      } finally {
        this.loading = false
      }
    },

    /**
     * 获取考试详情
     * @param {number} id - 考试ID
     */
    async fetchExam(id) {
      this.loading = true
      try {
        const data = await getExam(id)
        this.currentExam = data
        return data
      } finally {
        this.loading = false
      }
    },

    /**
     * 创建考试
     * @param {Object} examData - 考试数据
     */
    async createExam(examData) {
      const data = await apiCreateExam(examData)
      this.exams.unshift(data)
      return data
    },

    /**
     * 更新考试
     * @param {number} id - 考试ID
     * @param {Object} examData - 考试数据
     */
    async updateExam(id, examData) {
      const data = await apiUpdateExam(id, examData)
      // 更新本地列表中的数据
      const index = this.exams.findIndex(e => e.id === id)
      if (index !== -1) {
        this.exams[index] = data
      }
      // 如果当前查看的是这个考试，也更新当前考试
      if (this.currentExam?.id === id) {
        this.currentExam = data
      }
      return data
    },

    /**
     * 删除考试
     * @param {number} id - 考试ID
     */
    async deleteExam(id) {
      await apiDeleteExam(id)
      this.exams = this.exams.filter(e => e.id !== id)
      if (this.currentExam?.id === id) {
        this.currentExam = null
      }
    },

    /**
     * 检查即将开始的考试
     * 获取未来60分钟内的考试，用于提醒功能
     */
    async checkUpcomingExams() {
      try {
        const exams = await apiGetUpcomingExams(60)
        const now = new Date()

        // 计算每个考试的提醒状态
        const examList = exams.items || exams
        this.upcomingReminders = examList.map(exam => {
          const startTime = new Date(exam.start_time)
          const diffMinutes = Math.floor((startTime - now) / (1000 * 60))

          let reminderType = null
          let reminderText = ''

          if (diffMinutes <= 0) {
            reminderType = 'start'
            reminderText = '考试即将开始'
          } else if (diffMinutes <= 5) {
            reminderType = '5min'
            reminderText = '5分钟后开始'
          } else if (diffMinutes <= 15) {
            reminderType = '15min'
            reminderText = '15分钟后开始'
          }

          return {
            ...exam,
            diffMinutes,
            reminderType,
            reminderText
          }
        }).filter(exam => {
          // 过滤掉已关闭的提醒
          const dismissed = this.dismissedReminders[exam.id]
          return exam.reminderType && (!dismissed || !dismissed[exam.reminderType])
        })

        this.reminderChecked = true
        return this.upcomingReminders
      } catch (error) {
        console.error('[ExamStore] 检查即将开始的考试失败:', error)
        return []
      }
    },

    /**
     * 关闭提醒
     * @param {number} examId - 考试ID
     * @param {string} reminderType - 提醒类型 (15min/5min/start)
     */
    async dismissReminder(examId, reminderType) {
      // 本地记录已关闭的提醒
      if (!this.dismissedReminders[examId]) {
        this.dismissedReminders[examId] = {}
      }
      this.dismissedReminders[examId][reminderType] = true

      // 从待处理提醒列表中移除
      this.upcomingReminders = this.upcomingReminders.filter(
        r => !(r.id === examId && r.reminderType === reminderType)
      )

      // 同步到后端
      try {
        await apiDismissReminder(examId, reminderType)
      } catch (error) {
        console.warn('[ExamStore] 同步关闭提醒状态失败:', error)
      }
    },

    /**
     * 清理已过期的提醒记录
     * 移除已经结束考试的提醒记录，释放内存
     */
    clearExpiredReminders() {
      const now = new Date()
      const expiredExamIds = this.exams
        .filter(exam => new Date(exam.end_time) <= now)
        .map(exam => exam.id)

      // 清理已结束考试的提醒记录
      expiredExamIds.forEach(id => {
        if (this.dismissedReminders[id]) {
          delete this.dismissedReminders[id]
        }
      })
    },

    /**
     * 重置当前考试
     */
    clearCurrentExam() {
      this.currentExam = null
    },

    /**
     * 重置所有状态
     */
    reset() {
      this.exams = []
      this.currentExam = null
      this.upcomingReminders = []
      this.loading = false
      this.reminderChecked = false
      this.dismissedReminders = {}
    }
  }
})
