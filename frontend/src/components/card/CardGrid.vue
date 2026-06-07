<template>
  <div class="card-grid" :class="gridClass">
    <div 
      v-for="card in cards" 
      :key="card.id" 
      class="grid-item"
      :style="gridItemStyle"
    >
      <FileCard :card="card" @click="handleCardClick" />
    </div>
    
    <!-- 空状态 -->
    <div v-if="!cards?.length && !loading" class="empty-state">
      <el-empty description="暂无文档">
        <template #image>
          <el-icon :size="64" color="#c0c4cc">
            <Folder />
          </el-icon>
        </template>
      </el-empty>
    </div>
    
    <!-- 加载状态 -->
    <template v-if="loading">
      <div 
        v-for="i in skeletonCount" 
        :key="'skeleton-' + i" 
        class="grid-item"
        :style="gridItemStyle"
      >
        <SkeletonCard />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { Folder } from '@element-plus/icons-vue'
import FileCard from './FileCard.vue'
import SkeletonCard from '@/components/common/SkeletonCard.vue'
import { useResponsive } from '@/composables/useResponsive'

const props = defineProps({
  cards: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  // 自定义列数配置
  columns: {
    type: Object,
    default: () => ({
      xl: 4,    // >= 1200px
      lg: 4,    // >= 992px
      md: 3,    // >= 768px
      sm: 2,    // >= 576px
      xs: 1     // < 576px
    })
  },
  // 卡片间距
  gap: {
    type: [Number, String],
    default: 20
  }
})

const emit = defineEmits(['card-click'])

const { currentBreakpoint, isXl, isLg, isMd, isSm, isXs } = useResponsive()

// 计算当前列数
const currentColumns = computed(() => {
  if (isXl.value) return props.columns.xl
  if (isLg.value) return props.columns.lg
  if (isMd.value) return props.columns.md
  if (isSm.value) return props.columns.sm
  return props.columns.xs
})

// 网格类名
const gridClass = computed(() => {
  return `grid-cols-${currentColumns.value}`
})

// 网格项样式
const gridItemStyle = computed(() => {
  const gap = typeof props.gap === 'number' ? `${props.gap}px` : props.gap
  return {
    marginBottom: gap
  }
})

// 骨架屏数量
const skeletonCount = computed(() => {
  return currentColumns.value * 2
})

function handleCardClick(card) {
  if (!card || card instanceof Event) return
  emit('card-click', card)
}
</script>

<style scoped>
.card-grid {
  display: grid;
  gap: 20px;
  width: 100%;
}

/* 响应式网格列数 */
.grid-cols-1 {
  grid-template-columns: repeat(1, 1fr);
}

.grid-cols-2 {
  grid-template-columns: repeat(2, 1fr);
}

.grid-cols-3 {
  grid-template-columns: repeat(3, 1fr);
}

.grid-cols-4 {
  grid-template-columns: repeat(4, 1fr);
}

.grid-cols-5 {
  grid-template-columns: repeat(5, 1fr);
}

.grid-cols-6 {
  grid-template-columns: repeat(6, 1fr);
}

.grid-item {
  display: flex;
  flex-direction: column;
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .card-grid {
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .card-grid {
    gap: 12px;
  }
}

@media (max-width: 576px) {
  .card-grid {
    gap: 10px;
  }
}
</style>
