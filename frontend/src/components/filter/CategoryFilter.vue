<template>
  <div class="category-filter">
    <div class="filter-header">
      <h4>
        <el-icon><Folder /></el-icon>
        分类筛选
      </h4>
      <el-button 
        v-if="selectedCategory" 
        text 
        type="primary" 
        size="small"
        @click="clearSelection"
      >
        清除
      </el-button>
    </div>
    
    <div v-if="loading" class="filter-loading">
      <el-skeleton :rows="3" animated />
    </div>
    
    <div v-else class="category-tree">
      <!-- 全部分类 -->
      <div 
        class="category-item"
        :class="{ active: !selectedCategory }"
        @click="selectCategory(null)"
      >
        <el-icon><Grid /></el-icon>
        <span>全部</span>
        <span class="count">{{ totalCount }}</span>
      </div>
      
      <!-- 分类列表 -->
      <template v-for="category in categories" :key="category.id">
        <div 
          class="category-item"
          :class="{ 
            active: selectedCategory === category.id,
            expanded: expandedCategories.includes(category.id)
          }"
          @click="selectCategory(category.id)"
        >
          <el-icon v-if="category.children?.length" @click.stop="toggleExpand(category.id)">
            <ArrowRight v-if="!expandedCategories.includes(category.id)" />
            <ArrowDown v-else />
          </el-icon>
          <el-icon v-else><Folder /></el-icon>
          <span>{{ category.name }}</span>
          <span class="count">{{ category.count || 0 }}</span>
        </div>
        
        <!-- 子分类 -->
        <div 
          v-if="category.children?.length && expandedCategories.includes(category.id)"
          class="sub-categories"
        >
          <div 
            v-for="child in category.children" 
            :key="child.id"
            class="category-item sub"
            :class="{ active: selectedCategory === child.id }"
            @click="selectCategory(child.id)"
          >
            <el-icon><Folder /></el-icon>
            <span>{{ child.name }}</span>
            <span class="count">{{ child.count || 0 }}</span>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Folder, Grid, ArrowRight, ArrowDown } from '@element-plus/icons-vue'
import { cardApi } from '@/api/card'

const props = defineProps({
  modelValue: {
    type: [String, Number, null],
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const categories = ref([])
const loading = ref(false)
const expandedCategories = ref([])

const selectedCategory = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const totalCount = computed(() => {
  return categories.value.reduce((sum, cat) => sum + (cat.count || 0), 0)
})

async function loadCategories() {
  loading.value = true
  
  try {
    const data = await cardApi.getCategories()
    categories.value = data || []
  } catch (error) {
    console.error('加载分类失败:', error)
  } finally {
    loading.value = false
  }
}

function selectCategory(categoryId) {
  selectedCategory.value = categoryId
  emit('change', categoryId)
}

function clearSelection() {
  selectedCategory.value = null
  emit('change', null)
}

function toggleExpand(categoryId) {
  const index = expandedCategories.value.indexOf(categoryId)
  if (index > -1) {
    expandedCategories.value.splice(index, 1)
  } else {
    expandedCategories.value.push(categoryId)
  }
}

onMounted(() => {
  loadCategories()
})
</script>

<style scoped>
.category-filter {
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

.category-tree {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  color: #606266;
}

.category-item:hover {
  background: #f5f7fa;
}

.category-item.active {
  background: #ecf5ff;
  color: #409eff;
}

.category-item span {
  flex: 1;
}

.category-item .count {
  flex: none;
  font-size: 12px;
  color: #c0c4cc;
  background: #f0f2f5;
  padding: 2px 8px;
  border-radius: 10px;
}

.category-item.active .count {
  background: #409eff;
  color: #fff;
}

.category-item.sub {
  padding-left: 32px;
  font-size: 13px;
}

.sub-categories {
  margin-left: 12px;
  border-left: 2px solid #e4e7ed;
  padding-left: 8px;
}
</style>
