<template>
  <el-dialog
    v-model="visible"
    :title="notice?.title || '通知'"
    :width="isMobile ? '90%' : '480px'"
    :show-close="true"
    :close-on-click-modal="false"
    class="popup-notice"
    @close="handleClose"
  >
    <div class="notice-body">
      <div class="notice-icon-wrapper" :class="notice?.type || 'info'">
        <el-icon :size="48">
          <SuccessFilled v-if="notice?.type === 'success'" />
          <WarningFilled v-else-if="notice?.type === 'warning'" />
          <CircleCloseFilled v-else-if="notice?.type === 'error'" />
          <InfoFilled v-else />
        </el-icon>
      </div>

      <div class="notice-content">
        <h3 v-if="notice?.title">{{ notice.title }}</h3>
        <AnnouncementRenderer
          v-if="hasBlocks"
          :blocks="notice.content_blocks"
        />
        <template v-else>
          <p v-if="notice?.message">{{ notice.message }}</p>
          <p v-else-if="notice?.content">{{ notice.content }}</p>
          <div v-if="notice?.details" class="notice-details">{{ notice.details }}</div>
        </template>
      </div>

      <div v-if="notice?.actions?.length" class="notice-actions">
        <el-button
          v-for="action in notice.actions"
          :key="action.key || action.label"
          :type="action.type || 'default'"
          @click="handleAction(action)"
        >
          {{ action.label }}
        </el-button>
      </div>
    </div>

    <template #footer>
      <div class="notice-footer">
        <el-checkbox v-model="dontShowAgain">不再提示</el-checkbox>
        <el-button type="primary" @click="handleConfirm">
          {{ notice?.confirmText || '我知道了' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  CircleCloseFilled,
  InfoFilled,
  SuccessFilled,
  WarningFilled,
} from '@element-plus/icons-vue'
import AnnouncementRenderer from '@/components/announcement/AnnouncementRenderer.vue'
import { useResponsive } from '@/composables/useResponsive'

const props = defineProps({
  notice: {
    type: Object,
    default: null,
  },
  modelValue: {
    type: Boolean,
    default: false,
  },
  storageKey: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue', 'confirm', 'action', 'close'])

const router = useRouter()
const { isMobile } = useResponsive()
const dontShowAgain = ref(false)

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const hasBlocks = computed(() => Array.isArray(props.notice?.content_blocks) && props.notice.content_blocks.length > 0)

function handleConfirm() {
  if (dontShowAgain.value && props.storageKey) {
    localStorage.setItem(props.storageKey, 'hidden')
  }
  emit('confirm', props.notice)
  visible.value = false
}

function handleAction(action) {
  emit('action', { action, notice: props.notice })
  if (action.link) {
    router.push(action.link)
  }
  visible.value = false
}

function handleClose() {
  emit('close', props.notice)
}

watch(() => props.notice, (newNotice) => {
  if (newNotice && props.storageKey) {
    const hidden = localStorage.getItem(props.storageKey)
    if (hidden === 'hidden') {
      visible.value = false
    }
  }
}, { immediate: true })
</script>

<style scoped>
.popup-notice :deep(.el-dialog__body) {
  padding-top: 20px;
}

.notice-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.notice-icon-wrapper {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  margin-bottom: 20px;
}

.notice-icon-wrapper.info {
  background: #e6f7ff;
  color: #1890ff;
}

.notice-icon-wrapper.success {
  background: #f6ffed;
  color: #52c41a;
}

.notice-icon-wrapper.warning {
  background: #fffbe6;
  color: #faad14;
}

.notice-icon-wrapper.error {
  background: #fff2f0;
  color: #ff4d4f;
}

.notice-content {
  width: 100%;
}

.notice-content h3 {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.notice-content p {
  margin: 0 0 12px;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.notice-details {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  font-size: 13px;
  color: #909399;
  text-align: left;
  max-height: 200px;
  overflow-y: auto;
}

.notice-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
  justify-content: center;
}

.notice-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

@media (max-width: 768px) {
  .notice-icon-wrapper {
    width: 60px;
    height: 60px;
  }

  .notice-content h3 {
    font-size: 16px;
  }
}
</style>
