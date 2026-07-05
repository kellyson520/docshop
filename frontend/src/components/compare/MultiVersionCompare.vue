<template>
  <div class="multi-compare">
    <!-- 版本选择器 -->
    <div class="version-selector">
      <el-select 
        v-model="localSelectedVersions" 
        multiple 
        placeholder="选择要对比的版本"
        :multiple-limit="4"
        style="width: 100%; max-width: 400px;"
      >
        <el-option 
          v-for="v in versions" 
          :key="v.id" 
          :label="`v${v.version} - ${formatDate(v.created_at)}`" 
          :value="v.id"
        />
      </el-select>
      <el-button 
        type="primary" 
        @click="doCompare" 
        :loading="comparing"
        :disabled="localSelectedVersions.length < 2"
      >
        开始对比
      </el-button>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="comparing" class="compare-loading">
      <el-skeleton v-for="i in localSelectedVersions.length" :key="i" :rows="8" animated />
    </div>
    
    <!-- 横向对比视图 -->
    <div class="compare-panels" v-else-if="compareResults.length">
      <div 
        v-for="(result, idx) in compareResults" 
        :key="`${result.version_a_id}-${result.version_b_id}-${idx}`" 
        class="compare-panel"
      >
        <div class="panel-header">
          <h3>v{{ result.version_a_number }} → v{{ result.version_b_number }}</h3>
          <el-tag :type="result.has_diff ? 'warning' : 'success'" size="small">
            {{ result.has_diff ? '有差异' : '无差异' }}
          </el-tag>
        </div>
        <div class="panel-content">
          <div class="result-summary">
            <div class="summary-line">
              <el-tag :type="result.has_diff ? 'warning' : 'info'" size="small">
                {{ result.has_diff ? '有差异' : '无差异' }}
              </el-tag>
              <span class="summary-meta">v{{ result.version_a_number }} → v{{ result.version_b_number }}</span>
            </div>
            <p class="summary-text">
              {{ result.diff_summary || '未返回详细差异摘要' }}
            </p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 空状态 -->
    <div v-else class="empty-compare">
      <el-empty description="请选择至少2个版本进行对比">
        <template #image>
          <el-icon :size="64" color="#c0c4cc">
            <Sort />
          </el-icon>
        </template>
      </el-empty>
    </div>
    
    <!-- 对比统计 -->
    <div class="compare-stats" v-if="compareResults.length">
      <el-card shadow="never">
        <template #header>
          <span>对比统计</span>
        </template>
        <div class="stats-grid">
          <div class="stat-item" v-for="(stat, idx) in compareStats" :key="idx">
            <span class="stat-label">{{ stat.label }}</span>
            <span class="stat-value" :class="stat.class">{{ stat.value }}</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Sort } from '@element-plus/icons-vue'
import { cardApi } from '@/api/card'

const props = defineProps({
  cardId: {
    type: [String, Number],
    required: true
  },
  versionIds: {
    type: Array,
    default: () => []
  },
  fileType: {
    type: String,
    default: ''
  }
})

// 数据
const versions = ref([])
const localSelectedVersions = ref([])
const compareResults = ref([])
const comparing = ref(false)

// 初始化选中的版本
watch(() => props.versionIds, (newIds) => {
  if (newIds?.length >= 2) {
    localSelectedVersions.value = [...newIds]
  }
}, { immediate: true })

function normalizeDiffStats(diffData) {
  const stats = diffData?.stats || {}

  const additions =
    Number(stats.paragraphs_added || stats.pages_added || stats.rows_added || stats.sheets_added || 0) || 0
  const deletions =
    Number(stats.paragraphs_deleted || stats.pages_deleted || stats.rows_deleted || stats.sheets_deleted || 0) || 0
  const modifications =
    Number(
      stats.paragraphs_modified ||
      stats.pages_modified ||
      stats.total_cells_modified ||
      stats.cells_modified ||
      stats.tables_changed ||
      0
    ) || 0

  return {
    additions,
    deletions,
    modifications
  }
}

// 计算对比统计
const compareStats = computed(() => {
  if (!compareResults.value.length) return []

  const changedPairs = compareResults.value.filter((result) => result.has_diff).length
  const unchangedPairs = compareResults.value.length - changedPairs

  const versionCount = new Set(
    compareResults.value.flatMap((result) => [result.version_a_id, result.version_b_id])
  ).size

  return [
    { label: '参与版本', value: versionCount, class: '' },
    { label: '对比对数', value: compareResults.value.length, class: 'stat-warning' },
    { label: '有差异', value: changedPairs, class: 'stat-danger' },
    { label: '无差异', value: unchangedPairs, class: 'stat-success' }
  ]
})

// 加载版本列表
async function loadVersions() {
  try {
    const data = await cardApi.getVersions(props.cardId)
    versions.value = Array.isArray(data) ? data : (data?.versions || [])
  } catch (error) {
    ElMessage.error('加载版本列表失败: ' + error.message)
  }
}

// 执行对比
async function doCompare() {
  if (localSelectedVersions.value.length < 2) {
    ElMessage.warning('请至少选择2个版本进行对比')
    return
  }
  
  comparing.value = true
  compareResults.value = []
  
  try {
    const results = await cardApi.compareVersions(props.cardId, localSelectedVersions.value)
    compareResults.value = Array.isArray(results)
      ? results
      : (results?.compare_results || [])
  } catch (error) {
    ElMessage.error('对比失败: ' + error.message)
  } finally {
    comparing.value = false
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

// 初始化
onMounted(() => {
  loadVersions()
  
  // 如果有预选版本，自动开始对比
  if (props.versionIds?.length >= 2) {
    localSelectedVersions.value = [...props.versionIds]
    doCompare()
  }
})
</script>

<style scoped>
.multi-compare {
  min-height: 300px;
}

.version-selector {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.compare-loading {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 16px;
}

.compare-panels {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 16px;
}

.compare-panel {
  flex: 1;
  min-width: 300px;
  max-width: 500px;
  border: 1px solid #dcdfe6;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #dcdfe6;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.panel-date {
  font-size: 12px;
  color: #909399;
}

.panel-content {
  padding: 16px;
}

.result-summary {
  display: grid;
  gap: 10px;
}

.summary-line {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.summary-meta {
  font-size: 12px;
  color: #909399;
}

.summary-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: #303133;
}

.empty-compare {
  padding: 60px 20px;
  text-align: center;
}

.compare-stats {
  margin-top: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.stat-success { color: #67c23a; }
.stat-danger { color: #f56c6c; }
.stat-warning { color: #e6a23c; }

/* 响应式：移动端改为纵向排列 */
@media (max-width: 768px) {
  .compare-panels {
    flex-direction: column;
  }
  
  .compare-panel {
    min-width: 100%;
    max-width: 100%;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 576px) {
  .version-selector {
    flex-direction: column;
    align-items: stretch;
  }
  
  .version-selector .el-select {
    max-width: 100% !important;
  }
}
</style>
