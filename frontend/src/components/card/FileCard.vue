<template>
  <div class="file-card" role="button" tabindex="0" @click="handleClick" @keydown.enter="handleClick">
    <!-- 封面图片区域 -->
    <div class="card-cover">
      <img
        v-if="coverSrc && !coverLoadFailed"
        :src="coverSrc"
        alt="cover"
        loading="lazy"
        @error="coverLoadFailed = true"
      />
      <div v-else class="default-cover" :class="card.file_type">
        <!-- 根据文件类型显示默认图标 -->
        <el-icon :size="48">
          <Document v-if="card.file_type === 'pdf'" />
          <Document v-else-if="card.file_type === 'docx'" />
          <Grid v-else-if="card.file_type === 'xlsx'" />
          <Document v-else />
        </el-icon>
        <span>{{ fileTypeName }}</span>
      </div>
      <!-- 文件类型标签 -->
      <el-tag class="type-tag" :type="tagType" size="small">
        {{ card.file_type?.toUpperCase() || 'FILE' }}
      </el-tag>
    </div>
    
    <!-- 卡片内容 -->
    <div class="card-content">
      <h3 class="card-title">{{ card.display_name || card.filename || '未命名文档' }}</h3>
      <p class="card-desc" v-if="card.description">{{ card.description }}</p>
      
      <!-- 标签 -->
      <div class="card-tags" v-if="card.tags?.length">
        <el-tag 
          v-for="tag in displayTags" 
          :key="tag" 
          size="small"
          effect="plain"
        >
          {{ tag }}
        </el-tag>
        <el-tag v-if="card.tags.length > 3" size="small" type="info">
          +{{ card.tags.length - 3 }}
        </el-tag>
      </div>
      
      <!-- 底部信息 -->
      <div class="card-footer">
        <span class="version">
          <el-icon><Files /></el-icon>
          {{ card.version_count || 1 }} 版本
        </span>
        <span class="time">{{ formatDate(card.updated_at) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Document, Files, Grid } from '@element-plus/icons-vue'
import { resolveCoverUrl } from '@/utils/cover'

const props = defineProps({
  card: { 
    type: Object, 
    required: true 
  }
})

const emit = defineEmits(['click'])
const coverLoadFailed = ref(false)

const coverSrc = computed(() => resolveCoverUrl(props.card.cover_image))

watch(coverSrc, () => {
  coverLoadFailed.value = false
})

const fileTypeName = computed(() => {
  const types = { 
    pdf: 'PDF 文档', 
    docx: 'Word 文档', 
    xlsx: 'Excel 表格' 
  }
  return types[props.card.file_type] || '文档'
})

const tagType = computed(() => {
  const types = { 
    pdf: 'danger', 
    docx: 'primary', 
    xlsx: 'success' 
  }
  return types[props.card.file_type] || 'info'
})

const displayTags = computed(() => {
  return props.card.tags?.slice(0, 3) || []
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date
  
  // 小于1天显示相对时间
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    if (hours < 1) return '刚刚'
    return `${hours}小时前`
  }
  
  // 小于7天显示天数
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000)
    return `${days}天前`
  }
  
  // 否则显示日期
  return date.toLocaleDateString('zh-CN')
}

function handleClick() {
  emit('click', props.card)
}
</script>

<style scoped>
.file-card {
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #ebeef5;
}

.file-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.file-card:active {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition-duration: 0.1s;
}

.file-card:focus-visible {
  outline: 2px solid #409eff;
  outline-offset: 2px;
}

.card-cover {
  position: relative;
  height: 160px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.file-card:hover .card-cover img {
  transform: scale(1.05);
}

.default-cover {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #909399;
}

.default-cover.pdf {
  color: #f56c6c;
}

.default-cover.docx {
  color: #409eff;
}

.default-cover.xlsx {
  color: #67c23a;
}

.type-tag {
  position: absolute;
  top: 8px;
  right: 8px;
  font-weight: 600;
}

.card-content {
  padding: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-desc {
  font-size: 13px;
  color: #909399;
  margin: 0 0 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  min-height: 24px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #c0c4cc;
}

.version {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 响应式 */
@media (max-width: 768px) {
  .card-cover {
    height: 120px;
  }
  
  .card-content {
    padding: 12px;
  }
  
  .card-title {
    font-size: 14px;
  }
  
  .card-desc {
    font-size: 12px;
    margin-bottom: 8px;
  }
  
  .card-tags {
    margin-bottom: 8px;
  }
}

@media (max-width: 576px) {
  .card-cover {
    height: 100px;
  }
  
  .card-content {
    padding: 10px;
  }
  
  .card-title {
    font-size: 13px;
    margin-bottom: 6px;
  }
  
  .card-footer {
    font-size: 11px;
  }
}
</style>
