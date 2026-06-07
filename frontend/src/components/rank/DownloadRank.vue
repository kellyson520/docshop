<template>
  <div class="download-rank">
    <div class="rank-header">
      <h3>
        <el-icon><TrendCharts /></el-icon>
        下载排行榜
      </h3>
      <el-select v-model="period" size="small" @change="loadRank">
        <el-option label="今日" value="day" />
        <el-option label="本周" value="week" />
        <el-option label="本月" value="month" />
        <el-option label="全部" value="all" />
      </el-select>
    </div>
    
    <div v-if="loading" class="rank-loading">
      <el-skeleton v-for="i in 5" :key="i" :rows="1" animated />
    </div>
    
    <div v-else-if="rankList.length" class="rank-list">
      <div 
        v-for="(item, index) in rankList" 
        :key="item.id"
        class="rank-item"
        @click="handleClick(item)"
      >
        <div class="rank-num" :class="getRankClass(index)">
          {{ index + 1 }}
        </div>
        <div class="rank-info">
          <div class="rank-title">{{ item.display_name || item.filename }}</div>
          <div class="rank-meta">
            <el-tag size="small" :type="getFileTypeTag(item.file_type)">
              {{ item.file_type?.toUpperCase() }}
            </el-tag>
            <span class="download-count">
              <el-icon><Download /></el-icon>
              {{ formatCount(item.download_count) }} 次下载
            </span>
          </div>
        </div>
        <el-icon class="rank-arrow"><ArrowRight /></el-icon>
      </div>
    </div>
    
    <el-empty v-else description="暂无数据" :image-size="60" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { TrendCharts, Download, ArrowRight } from '@element-plus/icons-vue'
import { cardApi } from '@/api/card'

const props = defineProps({
  limit: {
    type: Number,
    default: 10
  }
})

const router = useRouter()

const period = ref('week')
const rankList = ref([])
const loading = ref(false)

async function loadRank() {
  loading.value = true
  
  try {
    const data = await cardApi.getDownloadRank({
      limit: props.limit,
      period: period.value
    })
    rankList.value = data || []
  } catch (error) {
    console.error('加载排行榜失败:', error)
  } finally {
    loading.value = false
  }
}

function getRankClass(index) {
  if (index === 0) return 'gold'
  if (index === 1) return 'silver'
  if (index === 2) return 'bronze'
  return ''
}

function getFileTypeTag(type) {
  const tags = { pdf: 'danger', docx: 'primary', xlsx: 'success' }
  return tags[type] || 'info'
}

function formatCount(count) {
  if (!count) return '0'
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`
  return count
}

function handleClick(item) {
  router.push(`/admin/cards/${item.id}`)
}

onMounted(() => {
  loadRank()
})
</script>

<style scoped>
.download-rank {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.rank-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.rank-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.rank-loading {
  padding: 8px;
}

.rank-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rank-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.rank-item:hover {
  background: #f5f7fa;
}

.rank-num {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 600;
  background: #f0f2f5;
  color: #909399;
}

.rank-num.gold {
  background: linear-gradient(135deg, #ffd700 0%, #ffb347 100%);
  color: #fff;
}

.rank-num.silver {
  background: linear-gradient(135deg, #c0c0c0 0%, #a8a8a8 100%);
  color: #fff;
}

.rank-num.bronze {
  background: linear-gradient(135deg, #cd7f32 0%, #b87333 100%);
  color: #fff;
}

.rank-info {
  flex: 1;
  min-width: 0;
}

.rank-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

.rank-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.download-count {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
}

.rank-arrow {
  color: #c0c4cc;
  transition: transform 0.2s;
}

.rank-item:hover .rank-arrow {
  transform: translateX(4px);
  color: #409eff;
}
</style>
