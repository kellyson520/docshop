<template>
  <div class="scroll-notice" v-if="notices.length && visible">
    <div class="scroll-container" ref="containerRef">
      <div class="scroll-content" :style="contentStyle">
        <span 
          v-for="(notice, index) in displayNotices" 
          :key="index"
          class="notice-item"
          @click="handleClick(notice)"
        >
          <el-icon v-if="notice.icon" class="notice-icon">
            <component :is="notice.icon" />
          </el-icon>
          {{ notice.message }}
          <el-tag 
            v-if="notice.tag" 
            :type="notice.tagType || 'info'" 
            size="small"
          >
            {{ notice.tag }}
          </el-tag>
        </span>
      </div>
    </div>
    <el-button 
      class="close-btn" 
      :icon="Close" 
      circle 
      size="small"
      @click="close"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Close } from '@element-plus/icons-vue'

const props = defineProps({
  notices: {
    type: Array,
    default: () => []
  },
  // 滚动速度（像素/秒）
  speed: {
    type: Number,
    default: 50
  },
  // 是否自动滚动
  autoScroll: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['click', 'close'])

const visible = ref(true)
const containerRef = ref(null)
const offset = ref(0)
let animationId = null
let containerWidth = 0
let contentWidth = 0

// 复制通知以实现无缝滚动
const displayNotices = computed(() => {
  if (props.notices.length === 0) return []
  // 复制两份实现无缝滚动
  return [...props.notices, ...props.notices]
})

const contentStyle = computed(() => ({
  transform: `translateX(-${offset.value}px)`
}))

function handleClick(notice) {
  emit('click', notice)
}

function close() {
  visible.value = false
  emit('close')
}

function animate() {
  if (!props.autoScroll || !containerRef.value) return
  
  containerWidth = containerRef.value.offsetWidth
  contentWidth = containerRef.value.scrollWidth / 2 // 实际内容宽度
  
  if (contentWidth <= containerWidth) {
    // 内容不够长，不需要滚动
    return
  }
  
  const move = (props.speed / 60) // 每帧移动距离
  
  offset.value += move
  
  // 当滚动完一遍后重置
  if (offset.value >= contentWidth) {
    offset.value = 0
  }
  
  animationId = requestAnimationFrame(animate)
}

onMounted(() => {
  if (props.autoScroll && props.notices.length) {
    // 延迟启动动画，等待 DOM 渲染
    setTimeout(() => {
      animate()
    }, 100)
  }
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
})
</script>

<style scoped>
.scroll-notice {
  display: flex;
  align-items: center;
  background: linear-gradient(90deg, #e6f7ff 0%, #bae7ff 100%);
  padding: 8px 16px;
  border-radius: 4px;
  margin-bottom: 16px;
}

.scroll-container {
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
}

.scroll-content {
  display: inline-flex;
  gap: 48px;
}

.notice-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #1890ff;
  cursor: pointer;
  padding-right: 48px;
}

.notice-item:hover {
  text-decoration: underline;
}

.notice-icon {
  font-size: 16px;
}

.close-btn {
  flex-shrink: 0;
  margin-left: 16px;
  background: transparent;
  border: none;
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.1);
}

/* 响应式 */
@media (max-width: 768px) {
  .scroll-notice {
    padding: 6px 12px;
  }
  
  .notice-item {
    font-size: 13px;
  }
}
</style>
