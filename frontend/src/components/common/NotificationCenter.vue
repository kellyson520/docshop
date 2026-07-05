<template>
  <div class="notification-center">
    <!-- 通知图标按钮 -->
    <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
      <el-button 
        :icon="Bell" 
        circle 
        @click="togglePanel"
      />
    </el-badge>
    
    <!-- 通知面板 -->
    <el-drawer
      v-model="showPanel"
      title="通知中心"
      direction="rtl"
      :size="isMobile ? '100%' : '400px'"
    >
      <!-- 通知类型筛选 -->
      <div class="notice-tabs">
        <el-radio-group v-model="activeTab" size="small">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="unread">未读</el-radio-button>
          <el-radio-button value="read">已读</el-radio-button>
        </el-radio-group>
        <el-button 
          v-if="unreadCount > 0" 
          text 
          type="primary" 
          @click="markAllRead"
        >
          全部已读
        </el-button>
      </div>
      
      <!-- 通知列表 -->
      <div class="notice-list">
        <div v-if="loading" class="loading-state">
          <el-skeleton v-for="i in 3" :key="i" :rows="2" animated />
        </div>
        
        <template v-else-if="filteredNotices.length">
          <div 
            v-for="notice in filteredNotices" 
            :key="notice.id"
            class="notice-item"
            :class="{ unread: !notice.is_read }"
            @click="handleNoticeClick(notice)"
          >
            <div class="notice-icon" :class="notice.type">
              <el-icon>
                <SuccessFilled v-if="notice.type === 'success'" />
                <WarningFilled v-else-if="notice.type === 'warning'" />
                <CircleCloseFilled v-else-if="notice.type === 'error'" />
                <InfoFilled v-else />
              </el-icon>
            </div>
            <div class="notice-content">
              <div class="notice-title">{{ notice.title }}</div>
              <div class="notice-message">{{ notice.message }}</div>
              <div class="notice-time">{{ formatTime(notice.created_at) }}</div>
            </div>
            <el-button 
              v-if="!notice.is_read"
              text
              type="primary"
              size="small"
              @click.stop="markRead(notice.id)"
            >
              标记已读
            </el-button>
          </div>
        </template>
        
        <el-empty v-else description="暂无通知" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  Bell, SuccessFilled, WarningFilled, CircleCloseFilled, InfoFilled 
} from '@element-plus/icons-vue'
import { cardApi } from '@/api/card'
import { useResponsive } from '@/composables/useResponsive'

const router = useRouter()
const { isMobile } = useResponsive()

// 数据
const notices = ref([])
const loading = ref(false)
const showPanel = ref(false)
const activeTab = ref('all')

// 计算属性
const unreadCount = computed(() => {
  return notices.value.filter(n => !n.is_read).length
})

const filteredNotices = computed(() => {
  if (activeTab.value === 'unread') {
    return notices.value.filter(n => !n.is_read)
  }
  if (activeTab.value === 'read') {
    return notices.value.filter(n => n.is_read)
  }
  return notices.value
})

// 判断请求是否被取消
function isRequestCanceled(error) {
  return error?.name === 'CanceledError' || error?.name === 'AbortError'
}

// 加载通知
async function loadNotices() {
  loading.value = true
  
  try {
    const data = await cardApi.getNotices()
    notices.value = data || []
  } catch (error) {
    if (isRequestCanceled(error)) return
    console.error('加载通知失败:', error)
  } finally {
    loading.value = false
  }
}

// 切换面板
function togglePanel() {
  showPanel.value = !showPanel.value
  if (showPanel.value) {
    loadNotices()
  }
}

// 标记已读
async function markRead(noticeId) {
  try {
    await cardApi.markNoticeRead(noticeId)
    const notice = notices.value.find(n => n.id === noticeId)
    if (notice) {
      notice.is_read = true
    }
  } catch (error) {
    ElMessage.error('标记失败: ' + error.message)
  }
}

// 全部标记已读
async function markAllRead() {
  try {
    await cardApi.markAllNoticesRead()
    notices.value.forEach(n => n.is_read = true)
    ElMessage.success('已全部标记为已读')
  } catch (error) {
    ElMessage.error('标记失败: ' + error.message)
  }
}

// 点击通知
function handleNoticeClick(notice) {
  // 标记已读
  if (!notice.is_read) {
    markRead(notice.id)
  }
  
  // 跳转到相关页面
  if (notice.link) {
    router.push(notice.link)
    showPanel.value = false
  }
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleDateString('zh-CN')
}

// 初始化
onMounted(() => {
  loadNotices()
})
</script>

<style scoped>
.notification-center {
  display: inline-block;
}

.notice-tabs {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.notice-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.loading-state {
  padding: 20px;
}

.notice-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  cursor: pointer;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease,
    background-color 0.2s ease,
    color 0.2s ease,
    opacity 0.2s ease;
}

.notice-item:hover {
  background: #eef1f6;
}

.notice-item.unread {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.notice-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 18px;
}

.notice-icon.info {
  background: #e6f7ff;
  color: #1890ff;
}

.notice-icon.success {
  background: #f6ffed;
  color: #52c41a;
}

.notice-icon.warning {
  background: #fffbe6;
  color: #faad14;
}

.notice-icon.error {
  background: #fff2f0;
  color: #ff4d4f;
}

.notice-content {
  flex: 1;
  min-width: 0;
}

.notice-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  margin-bottom: 4px;
}

.notice-message {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notice-time {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
