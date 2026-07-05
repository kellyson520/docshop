<template>
  <div class="rank-page">
    <div class="page-header">
      <h1>
        <el-icon><View /></el-icon>
        访问排行榜
      </h1>
      <div class="period-selector">
        <el-radio-group v-model="period" @change="loadRank">
          <el-radio-button value="day">今日</el-radio-button>
          <el-radio-button value="week">本周</el-radio-button>
          <el-radio-button value="month">本月</el-radio-button>
          <el-radio-button value="all">全部</el-radio-button>
        </el-radio-group>
      </div>
    </div>
    
    <div class="rank-content">
      <!-- 左侧排行榜 -->
      <div class="rank-main">
        <el-alert
          v-if="errorMessage"
          :title="errorMessage"
          type="error"
          show-icon
          :closable="false"
          class="rank-error"
        />
        <div v-if="loading" class="loading-state">
          <el-skeleton v-for="i in 10" :key="i" :rows="2" animated />
        </div>
        
        <div v-else-if="rankList.length" class="rank-list">
          <div 
            v-for="(item, index) in rankList" 
            :key="item.id"
            class="rank-card"
            @click="goDetail(item)"
          >
            <div class="rank-badge" :class="getRankClass(index)">
              <span class="rank-num">{{ index + 1 }}</span>
              <el-icon v-if="index < 3" class="medal">
                <Trophy />
              </el-icon>
            </div>
            
            <div class="card-cover">
              <img v-if="resolveCoverUrl(item.cover_image)" :src="resolveCoverUrl(item.cover_image)" alt="cover" />
              <div v-else class="default-cover" :class="item.file_type">
                <el-icon :size="32"><Document /></el-icon>
              </div>
            </div>
            
            <div class="card-info">
              <h3 class="card-title">{{ item.display_name || item.filename }}</h3>
              <p class="card-desc" v-if="item.description">{{ item.description }}</p>
              
              <div class="card-meta">
                <el-tag size="small" :type="getFileTypeTag(item.file_type)">
                  {{ item.file_type?.toUpperCase() }}
                </el-tag>
                <span class="visit-count">
                  <el-icon><View /></el-icon>
                  {{ formatCount(item.visit_count) }} 次访问
                </span>
                <span class="update-time">{{ formatDate(item.updated_at) }}</span>
              </div>
            </div>
            
            <!-- 趋势指示 -->
            <div class="trend-badge" :class="item.trend">
              <el-icon v-if="item.trend === 'up'"><CaretTop /></el-icon>
              <el-icon v-else-if="item.trend === 'down'"><CaretBottom /></el-icon>
            </div>
            
            <el-icon class="arrow-icon"><ArrowRight /></el-icon>
          </div>
        </div>
        
        <el-empty v-else description="暂无访问数据" />
      </div>
      
      <!-- 右侧统计 -->
      <div class="rank-sidebar">
        <el-card shadow="never" class="stats-card">
          <template #header>
            <span>访问统计</span>
          </template>
          <div class="stats-content">
            <div class="stat-item">
              <span class="stat-value">{{ totalVisits }}</span>
              <span class="stat-label">总访问次数</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ rankList.length }}</span>
              <span class="stat-label">文档数量</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ avgVisits }}</span>
              <span class="stat-label">平均访问</span>
            </div>
          </div>
        </el-card>
        
        <!-- 访问趋势图表占位 -->
        <el-card shadow="never" class="trend-card">
          <template #header>
            <span>访问趋势</span>
          </template>
          <div class="trend-chart">
            <el-icon :size="48" color="#c0c4cc"><TrendCharts /></el-icon>
            <p>访问趋势图表</p>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { View, ArrowRight, Document, Trophy, CaretTop, CaretBottom, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { cardApi } from '@/api/card'
import { resolveCoverUrl } from '@/utils/cover'

const router = useRouter()

const period = ref('week')
const rankList = ref([])
const loading = ref(false)
const errorMessage = ref('')

// 统计数据
const totalVisits = computed(() => {
  return rankList.value.reduce((sum, item) => sum + (item.visit_count || 0), 0)
})

const avgVisits = computed(() => {
  if (!rankList.value.length) return 0
  return Math.round(totalVisits.value / rankList.value.length)
})

async function loadRank() {
  loading.value = true
  errorMessage.value = ''
  
  try {
    const data = await cardApi.getVisitRank({
      limit: 20,
      period: period.value
    })
    rankList.value = data || []
  } catch (error) {
    console.error('Failed to load rank:', error)
    rankList.value = []
    errorMessage.value = error.message || 'Failed to load visit rank'
    ElMessage.error(errorMessage.value)
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

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function goDetail(item) {
  router.push(`/admin/cards/${item.id}`)
}

onMounted(() => {
  loadRank()
})
</script>

<style scoped>
.rank-page {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.rank-content {
  display: flex;
  gap: 24px;
}

.rank-main {
  flex: 1;
}

.loading-state {
  padding: 20px;
}

.rank-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rank-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: box-shadow 0.2s ease, border-color 0.2s ease, background-color 0.2s ease;
}

.rank-card:hover {
  transform: none;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.rank-badge {
  flex-shrink: 0;
  width: 50px;
  height: 50px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #f0f2f5;
}

.rank-badge.gold {
  background: linear-gradient(135deg, #ffd700 0%, #ffb347 100%);
  color: #fff;
}

.rank-badge.silver {
  background: linear-gradient(135deg, #c0c0c0 0%, #a8a8a8 100%);
  color: #fff;
}

.rank-badge.bronze {
  background: linear-gradient(135deg, #cd7f32 0%, #b87333 100%);
  color: #fff;
}

.rank-num {
  font-size: 18px;
  font-weight: 700;
}

.medal {
  font-size: 12px;
}

.card-cover {
  flex-shrink: 0;
  width: 80px;
  height: 80px;
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface-muted, #f6f8fb);
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.default-cover {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary, #7a8798);
}

.default-cover.pdf { color: var(--color-danger, #b42318); }
.default-cover.docx { color: var(--workspace-blue, #2f5d8c); }
.default-cover.xlsx { color: var(--workspace-accent, #0f766e); }

.card-info {
  flex: 1;
  min-width: 0;
}

.card-title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #172033);
}

.card-desc {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--text-tertiary, #7a8798);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.visit-count,
.update-time {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-tertiary, #7a8798);
}

.trend-badge {
  font-size: 16px;
}

.trend-badge.up {
  color: var(--workspace-accent, #0f766e);
}

.trend-badge.down {
  color: var(--color-danger, #b42318);
}

.arrow-icon {
  color: var(--text-placeholder, #a8b2bf);
  transition: color 0.2s ease;
}

.rank-card:hover .arrow-icon {
  transform: none;
  color: var(--workspace-blue, #2f5d8c);
}

/* 侧边栏 */
.rank-sidebar {
  width: 300px;
  flex-shrink: 0;
}

.stats-card,
.trend-card {
  margin-bottom: 20px;
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--workspace-blue, #2f5d8c);
}

.stat-label {
  font-size: 13px;
  color: var(--text-tertiary, #7a8798);
}

.trend-chart {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #c0c4cc;
}

.trend-chart p {
  margin: 12px 0 0;
  font-size: 14px;
}

/* 响应式 */
@media (max-width: 992px) {
  .rank-content {
    flex-direction: column;
  }
  
  .rank-sidebar {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .rank-page {
    padding: 16px;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .rank-card {
    padding: 16px;
    gap: 12px;
  }
  
  .card-cover {
    width: 60px;
    height: 60px;
  }
}
</style>
