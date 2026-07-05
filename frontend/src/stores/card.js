/**
 * 卡片状态管理
 * 管理卡片列表、详情、筛选状态、分页
 */

import { defineStore } from 'pinia'
import { resolveCoverUrl } from '@/utils/cover'
import { upload } from '@/api/client'

export const useCardStore = defineStore('card', {
  state: () => ({
    // 卡片列表
    cards: [],
    // 当前卡片详情
    currentCard: null,
    // 列表总数（用于分页）
    total: 0,
    // 当前页码
    currentPage: 1,
    // 每页数量
    pageSize: 20,
    // 筛选条件
    filters: {
      keyword: '',       // 搜索关键词
      status: '',        // 状态筛选
      category: '',      // 分类筛选
      sortBy: 'created_at', // 排序字段
      sortOrder: 'desc'  // 排序方向
    },
    // 加载状态
    loading: false,
    // 详情加载状态
    detailLoading: false,
    // 错误信息
    error: null
  }),

  getters: {
    /** 是否有更多数据 */
    hasMore: (state) => state.currentPage * state.pageSize < state.total,

    /** 总页数 */
    totalPages: (state) => Math.ceil(state.total / state.pageSize),

    /** 当前筛选条件是否有效（非空） */
    hasActiveFilters: (state) => {
      return !!(state.filters.keyword || state.filters.status || state.filters.category)
    }
  },

  actions: {
    /**
     * 获取卡片列表
     * @param {Object} [params] - 额外请求参数
     * @param {boolean} [append=false] - 是否追加到现有列表（用于加载更多）
     * @returns {Promise} 请求结果
     */
    async fetchCards(params = {}, append = false) {
      this.loading = true
      this.error = null
      try {
        // 合并筛选条件和分页参数
        const queryParams = {
          ...this.filters,
          page: this.currentPage,
          page_size: this.pageSize,
          ...params
        }

        // 动态导入 API 方法，避免循环依赖
        const { cardApi } = await import('@/api/card')
        const data = await cardApi.getList(queryParams)
        const items = (data.items || data || []).map((card) => ({
          ...card,
          cover_image: resolveCoverUrl(card.cover_image)
        }))

        if (append) {
          this.cards = [...this.cards, ...items]
        } else {
          this.cards = items
        }
        this.total = data.total || 0
        return data
      } catch (error) {
        this.error = error.message || '获取卡片列表失败'
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 获取卡片详情
     * @param {number|string} id - 卡片 ID
     * @returns {Promise} 卡片详情
     */
    async fetchCardDetail(id) {
      this.detailLoading = true
      this.error = null
      try {
        const { cardApi } = await import('@/api/card')
        const data = await cardApi.getDetail(id)
        const card = { ...data, cover_image: resolveCoverUrl(data.cover_image) }
        this.currentCard = card
        return card
      } catch (error) {
        this.error = error.message || '获取卡片详情失败'
        throw error
      } finally {
        this.detailLoading = false
      }
    },

    /**
     * 更新卡片信息
     * @param {number|string} id - 卡片 ID
     * @param {Object} cardData - 更新数据
     * @returns {Promise} 更新后的卡片信息
     */
    async updateCardInfo(id, cardData) {
      this.error = null
      try {
        const { cardApi } = await import('@/api/card')
        const data = await cardApi.updateInfo(id, cardData)

        // 更新列表中的对应项
        const index = this.cards.findIndex((c) => c.id === id)
        if (index !== -1) {
          this.cards.splice(index, 1, { ...this.cards[index], ...data })
        }

        // 更新当前详情（如果是同一张卡片）
        if (this.currentCard?.id === id) {
          this.currentCard = { ...this.currentCard, ...data }
        }

        return data
      } catch (error) {
        this.error = error.message || '更新卡片信息失败'
        throw error
      }
    },

    /**
     * 上传卡片封面
     * @param {number|string} id - 卡片 ID
     * @param {File} file - 封面文件
     * @param {Function} [onProgress] - 上传进度回调
     * @returns {Promise} 上传结果
     */
    async uploadCover(id, file, onProgress) {
      this.error = null
      try {
        const formData = new FormData()
        formData.append('cover', file)

        const data = await upload(`/cards/${id}/cover`, formData, onProgress)

        // 更新当前详情的封面
        if (this.currentCard?.id === id) {
          const coverImage = resolveCoverUrl(data.cover_image || data.cover_url || data.relative_path)
          this.currentCard = { ...this.currentCard, cover_image: coverImage }
        }

        return data
      } catch (error) {
        this.error = error.message || '上传封面失败'
        throw error
      }
    },

    /**
     * 设置筛选条件
     * @param {Object} filters - 筛选条件（部分更新）
     */
    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
      // 筛选条件变更时重置到第一页
      this.currentPage = 1
    },

    /**
     * 重置筛选条件
     */
    resetFilters() {
      this.filters = {
        keyword: '',
        status: '',
        category: '',
        sortBy: 'created_at',
        sortOrder: 'desc'
      }
      this.currentPage = 1
    },

    /**
     * 设置当前页码
     * @param {number} page - 页码
     */
    setPage(page) {
      this.currentPage = page
    },

    /**
     * 加载下一页
     * @returns {Promise} 请求结果
     */
    async loadMore() {
      if (!this.hasMore || this.loading) return
      this.currentPage++
      return this.fetchCards({}, true)
    },

    /**
     * 清除错误信息
     */
    clearError() {
      this.error = null
    },

    /**
     * 重置所有状态
     */
    reset() {
      this.cards = []
      this.currentCard = null
      this.total = 0
      this.currentPage = 1
      this.loading = false
      this.detailLoading = false
      this.error = null
      this.resetFilters()
    }
  }
})
