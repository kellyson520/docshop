<template>
  <div class="feature-card" :class="{ 'hovered': isHovered }" @mouseenter="isHovered = true" @mouseleave="isHovered = false">
    <div class="feature-icon" :style="iconStyle">
      <el-icon :size="28">
        <component :is="icon" />
      </el-icon>
    </div>
    <h3 class="feature-title">{{ title }}</h3>
    <p class="feature-description">{{ description }}</p>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  icon: {
    type: String,
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
  gradient: {
    type: String,
    default: 'blue'
  }
})

const isHovered = ref(false)

const iconStyle = computed(() => {
  const gradients = {
    blue: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    green: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
    orange: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    purple: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    yellow: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    cyan: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)'
  }
  return {
    background: gradients[props.gradient] || gradients.blue
  }
})
</script>

<style scoped>
.feature-card {
  background: var(--bg-secondary, #ffffff);
  border-radius: 16px;
  padding: 32px 24px;
  text-align: center;
  transition:
    transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    background-color 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    color 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid var(--border-color, #e4e7ed);
  cursor: default;
}

.feature-card.hovered {
  transform: translateY(-8px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
}

.feature-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  color: #fff;
  transition: transform 0.3s ease;
}

.feature-card.hovered .feature-icon {
  transform: scale(1.1) rotate(5deg);
}

.feature-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin: 0 0 12px;
  line-height: 1.4;
}

.feature-description {
  font-size: 14px;
  color: var(--text-secondary, #606266);
  line-height: 1.6;
  margin: 0;
}

/* 暗色模式适配 */
[data-theme="dark"] .feature-card {
  background: var(--bg-secondary, #1d1d1d);
  border-color: var(--border-color, #414243);
}

[data-theme="dark"] .feature-card.hovered {
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}
</style>
