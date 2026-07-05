<template>
  <div class="step-card" :class="{ 'reversed': reversed }">
    <div class="step-content">
      <div class="step-number">{{ stepNumber }}</div>
      <h3 class="step-title">{{ title }}</h3>
      <p class="step-description">{{ description }}</p>
    </div>
    <div class="step-image">
      <div class="image-placeholder">
        <el-icon :size="48" color="#909399">
          <component :is="icon || 'Picture'" />
        </el-icon>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  stepNumber: {
    type: Number,
    required: true
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    required: true
  },
  icon: {
    type: String,
    default: 'Picture'
  },
  reversed: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.step-card {
  display: flex;
  align-items: center;
  gap: 60px;
  padding: 40px 0;
}

.step-card.reversed {
  flex-direction: row-reverse;
}

.step-content {
  flex: 1;
  max-width: 480px;
}

.step-number {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
}

.step-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin: 0 0 16px;
  line-height: 1.3;
}

.step-description {
  font-size: 16px;
  color: var(--text-secondary, #606266);
  line-height: 1.7;
  margin: 0;
}

.step-image {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
}

.image-placeholder {
  width: 100%;
  max-width: 400px;
  aspect-ratio: 16 / 10;
  background: var(--bg-secondary, #f5f7fa);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed var(--border-color, #dcdfe6);
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease,
    border-color 0.3s ease,
    background-color 0.3s ease,
    color 0.3s ease,
    opacity 0.3s ease;
}

.step-card:hover .image-placeholder {
  border-color: #667eea;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
}

/* 响应式适配 */
@media (max-width: 768px) {
  .step-card,
  .step-card.reversed {
    flex-direction: column;
    gap: 32px;
    text-align: center;
  }

  .step-content {
    max-width: 100%;
  }

  .step-number {
    margin: 0 auto 20px;
  }

  .step-title {
    font-size: 22px;
  }

  .step-description {
    font-size: 15px;
  }

  .image-placeholder {
    max-width: 100%;
  }
}

/* 暗色模式适配 */
[data-theme="dark"] .image-placeholder {
  background: var(--bg-secondary, #1d1d1d);
  border-color: var(--border-color, #414243);
}
</style>
