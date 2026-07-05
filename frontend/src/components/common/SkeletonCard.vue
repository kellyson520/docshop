<!--
  卡片骨架屏组件
  用于项目卡片等内容的加载占位
-->
<template>
  <div class="skeleton-card-grid">
    <div
      v-for="i in count"
      :key="i"
      class="skeleton-col"
    >
      <el-card shadow="hover" class="skeleton-card">
        <!-- 头部骨架 -->
        <div class="skeleton-header">
          <el-skeleton-item variant="text" class="skeleton-title" />
          <el-skeleton-item variant="circle" class="skeleton-tag" />
        </div>
        
        <!-- 内容骨架 -->
        <div class="skeleton-body">
          <el-skeleton-item variant="p" class="skeleton-line" />
          <el-skeleton-item variant="p" class="skeleton-line skeleton-line--short" />
        </div>
        
        <!-- 底部骨架 -->
        <div class="skeleton-footer">
          <el-skeleton-item variant="text" class="skeleton-meta" />
          <el-skeleton-item variant="text" class="skeleton-meta" />
        </div>
        
        <!-- 操作按钮骨架 -->
        <div class="skeleton-actions">
          <el-skeleton-item variant="text" class="skeleton-action" />
          <el-skeleton-item variant="text" class="skeleton-action" />
          <el-skeleton-item variant="text" class="skeleton-action" />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
defineProps({
  /**
   * 骨架屏数量
   */
  count: {
    type: Number,
    default: 6
  }
})
</script>

<style scoped>
.skeleton-col {
  min-width: 0;
}

.skeleton-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}

.skeleton-card {
  height: 100%;
  padding: 8px;
  border-radius: var(--radius-card, 14px);
}

.skeleton-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.skeleton-title {
  width: 60%;
  height: 20px;
}

.skeleton-tag {
  width: 40px;
  height: 24px;
  border-radius: 4px;
}

.skeleton-body {
  margin-bottom: 16px;
}

.skeleton-line {
  width: 100%;
  height: 16px;
  margin-bottom: 8px;
}

.skeleton-line--short {
  width: 70%;
}

.skeleton-footer {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}

.skeleton-meta {
  width: 80px;
  height: 14px;
}

.skeleton-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

.skeleton-action {
  width: 60px;
  height: 20px;
}

@media (max-width: 767px) {
  .skeleton-card-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .skeleton-actions {
    justify-content: stretch;
  }

  .skeleton-action {
    flex: 1;
  }
}
</style>
