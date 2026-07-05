<!--
  表格骨架屏组件
  用于表格数据的加载占位
-->
<template>
  <div class="skeleton-table">
    <!-- 工具栏骨架 -->
    <div v-if="showToolbar" class="skeleton-toolbar">
      <el-skeleton-item variant="button" class="skeleton-btn" />
      <el-skeleton-item variant="button" class="skeleton-btn" />
      <el-skeleton-item variant="input" class="skeleton-search" />
    </div>
    
    <!-- 表头骨架 -->
    <div class="skeleton-header">
      <el-skeleton-item
        v-for="i in columns"
        :key="i"
        variant="text"
        class="skeleton-th"
        :style="{ width: getColumnWidth(i) }"
      />
    </div>
    
    <!-- 表格行骨架 -->
    <div
      v-for="row in rows"
      :key="row"
      class="skeleton-row"
    >
      <el-skeleton-item
        v-for="col in columns"
        :key="col"
        variant="text"
        class="skeleton-td"
        :style="{ width: getColumnWidth(col, true) }"
      />
    </div>
    
    <!-- 分页骨架 -->
    <div v-if="showPagination" class="skeleton-pagination">
      <el-skeleton-item variant="text" class="skeleton-page-item" />
      <el-skeleton-item variant="text" class="skeleton-page-item" />
      <el-skeleton-item variant="text" class="skeleton-page-item" />
      <el-skeleton-item variant="text" class="skeleton-page-item" />
      <el-skeleton-item variant="text" class="skeleton-page-item" />
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  /**
   * 表格行数
   */
  rows: {
    type: Number,
    default: 5
  },
  /**
   * 表格列数
   */
  columns: {
    type: Number,
    default: 4
  },
  /**
   * 是否显示工具栏
   */
  showToolbar: {
    type: Boolean,
    default: true
  },
  /**
   * 是否显示分页
   */
  showPagination: {
    type: Boolean,
    default: true
  }
})

/**
 * 获取列宽
 * @param {number} index - 列索引
 * @param {boolean} isData - 是否为数据行
 * @returns {string}
 */
function getColumnWidth(index, isData = false) {
  // 生成一些变化的宽度，使骨架屏看起来更自然
  const widths = ['25%', '20%', '30%', '15%', '10%']
  const dataWidths = ['23%', '18%', '28%', '14%', '12%']
  
  const list = isData ? dataWidths : widths
  return list[(index - 1) % list.length]
}
</script>

<style scoped>
.skeleton-table {
  background-color: #fff;
  border: 1px solid var(--border-color-light, #ebeef5);
  border-radius: var(--radius-card, 14px);
  overflow: hidden;
}

.skeleton-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
}

.skeleton-btn {
  width: 80px;
  height: 32px;
}

.skeleton-search {
  width: min(240px, 100%);
  height: 32px;
  margin-left: auto;
}

.skeleton-header {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
  min-width: 560px;
}

.skeleton-th {
  flex: 0 0 auto;
  height: 16px;
  margin-right: 20px;
}

.skeleton-th:last-child {
  margin-right: 0;
}

.skeleton-row {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
  min-width: 560px;
}

.skeleton-row:last-child {
  border-bottom: none;
}

.skeleton-td {
  flex: 0 0 auto;
  height: 14px;
  margin-right: 20px;
}

.skeleton-td:last-child {
  margin-right: 0;
}

.skeleton-pagination {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid #ebeef5;
}

.skeleton-page-item {
  width: 32px;
  height: 32px;
  border-radius: 4px;
}

.skeleton-page-item:first-child,
.skeleton-page-item:last-child {
  width: 60px;
}

@media (max-width: 767px) {
  .skeleton-table {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .skeleton-toolbar {
    padding: 12px;
  }

  .skeleton-search {
    flex: 1 0 100%;
    margin-left: 0;
  }

  .skeleton-pagination {
    justify-content: center;
    padding: 12px;
  }
}
</style>
