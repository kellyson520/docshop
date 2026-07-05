<template>
  <div class="tag-filter">
    <div class="filter-header">
      <h4>
        <el-icon><PriceTag /></el-icon>
        标签筛选
      </h4>
      <el-button 
        v-if="selectedTags.length" 
        text 
        type="primary" 
        size="small"
        @click="clearSelection"
      >
        清除全部
      </el-button>
    </div>
    
    <div v-if="loading" class="filter-loading">
      <el-skeleton :rows="3" animated />
    </div>
    
    <div v-else class="tag-cloud">
      <el-tag
        v-for="tag in tags"
        :key="tag.name || tag"
        :type="isSelected(tag.name || tag) ? 'primary' : 'info'"
        :effect="isSelected(tag.name || tag) ? 'dark' : 'plain'"
        :size="getTagSize(tag)"
        class="tag-item"
        @click="toggleTag(tag.name || tag)"
      >
        {{ tag.name || tag }}
        <span v-if="tag.count" class="tag-count">({{ tag.count }})</span>
      </el-tag>
    </div>
    
    <!-- 已选标签 -->
    <div v-if="selectedTags.length" class="selected-tags">
      <span class="selected-label">已选:</span>
      <el-tag
        v-for="tag in selectedTags"
        :key="tag"
        closable
        type="primary"
        @close="toggleTag(tag)"
      >
        {{ tag }}
      </el-tag>
    </div>
    
    <!-- 搜索标签 -->
    <div class="tag-search" v-if="showSearch">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索标签..."
        size="small"
        clearable
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { PriceTag, Search } from '@element-plus/icons-vue'
import { cardApi } from '@/api/card'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  showSearch: {
    type: Boolean,
    default: false
  },
  // 是否显示标签数量
  showCount: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const allTags = ref([])
const loading = ref(false)
const searchKeyword = ref('')

const selectedTags = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 过滤后的标签
const tags = computed(() => {
  if (!searchKeyword.value) return allTags.value
  
  const keyword = searchKeyword.value.toLowerCase()
  return allTags.value.filter(tag => {
    const name = (tag.name || tag).toLowerCase()
    return name.includes(keyword)
  })
})

async function loadTags() {
  loading.value = true
  
  try {
    const data = await cardApi.getTags()
    allTags.value = data || []
  } catch (error) {
    console.error('加载标签失败:', error)
  } finally {
    loading.value = false
  }
}

function isSelected(tag) {
  return selectedTags.value.includes(tag)
}

function toggleTag(tag) {
  const index = selectedTags.value.indexOf(tag)
  if (index > -1) {
    selectedTags.value = selectedTags.value.filter(t => t !== tag)
  } else {
    selectedTags.value = [...selectedTags.value, tag]
  }
  emit('change', selectedTags.value)
}

function clearSelection() {
  selectedTags.value = []
  emit('change', [])
}

function getTagSize(tag) {
  // 根据标签数量决定大小
  const count = tag.count || 0
  if (count >= 100) return 'large'
  if (count >= 10) return 'default'
  return 'small'
}

onMounted(() => {
  loadTags()
})
</script>

<style scoped>
.tag-filter {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.filter-header h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.filter-loading {
  padding: 8px;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  cursor: pointer;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease,
    background-color 0.2s ease,
    color 0.2s ease,
    opacity 0.2s ease;
  user-select: none;
}

.tag-item:hover {
  transform: scale(1.05);
}

.tag-count {
  margin-left: 4px;
  font-size: 10px;
  opacity: 0.8;
}

.selected-tags {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.selected-label {
  font-size: 13px;
  color: #909399;
}

.tag-search {
  margin-top: 16px;
}

/* 响应式 */
@media (max-width: 768px) {
  .tag-cloud {
    gap: 6px;
  }
  
  .tag-item {
    font-size: 12px;
  }
}
</style>
