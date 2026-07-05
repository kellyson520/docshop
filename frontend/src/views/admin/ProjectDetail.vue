<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <PageHeader
      title="项目详情"
      :breadcrumbs="breadcrumbs"
      :subtitle="project?.name"
    >
      <template #actions>
        <el-button @click="router.push('/admin/projects')">
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>
      </template>
    </PageHeader>

    <!-- 项目信息卡片 -->
    <el-card v-loading="loading" shadow="never" class="project-info-card mb-4">
      <div class="project-info">
        <div class="info-left">
          <h2>{{ project?.name }}</h2>
          <p class="project-desc">{{ project?.description || '暂无描述' }}</p>
          <div class="project-meta">
            <el-tag v-if="project?.is_public" type="success" size="small">公开</el-tag>
            <el-tag v-else size="small">私有</el-tag>
            <span class="meta-divider">|</span>
            <span>创建于 {{ formatDate(project?.created_at) }}</span>
            <span class="meta-divider">|</span>
            <span>{{ files.length }} 个文件</span>
          </div>
        </div>
        <div class="info-right">
          <el-button type="warning" plain @click="openProjectAccessDialog" class="btn-hover-lift">
            <el-icon><Lock /></el-icon>
            公开浏览权限
          </el-button>
          <el-button type="primary" plain @click="openShareDialog('project')" class="btn-hover-lift">
            <el-icon><Share /></el-icon>
            分享项目
          </el-button>
          <el-button type="primary" @click="goToUpload" class="btn-hover-lift">
            <el-icon><Upload /></el-icon>
            上传文件
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 预览生成管理 -->
    <el-card shadow="never" class="preview-ops-card mb-4">
      <template #header>
        <div class="preview-ops-header">
          <div>
            <span class="preview-ops-title">预览生成管理</span>
            <span class="preview-ops-subtitle">Word / PDF 异步队列、缓存容量与失败处理</span>
          </div>
          <el-button size="small" :loading="previewOpsLoading" @click="fetchPreviewStatuses">
            <el-icon><RefreshRight /></el-icon>
            刷新状态
          </el-button>
        </div>
      </template>

      <div class="preview-summary-grid">
        <div class="preview-summary-item preview-summary-ready">
          <span class="summary-label">Ready</span>
          <strong>{{ previewSummary.ready || 0 }}</strong>
          <small>已就绪</small>
        </div>
        <div class="preview-summary-item preview-summary-active">
          <span class="summary-label">Queue</span>
          <strong>{{ previewSummary.active || 0 }}</strong>
          <small>排队/生成中</small>
        </div>
        <div class="preview-summary-item preview-summary-problem">
          <span class="summary-label">Issues</span>
          <strong>{{ previewSummary.problem || 0 }}</strong>
          <small>失败/中断</small>
        </div>
        <div class="preview-summary-item preview-summary-storage">
          <span class="summary-label">Storage</span>
          <strong>{{ formatFileSize(previewSummary.storage_bytes || 0) }}</strong>
          <small>生成缓存</small>
        </div>
      </div>

      <div class="preview-diagnostics-grid">
        <div class="preview-diagnostic-card preview-storage-breakdown">
          <span class="summary-label">缓存拆分</span>
          <strong>PDF {{ formatFileSize(previewStorageBreakdown.pdf_bytes || 0) }}</strong>
          <small>图片 {{ formatFileSize(previewStorageBreakdown.image_bytes || 0) }}</small>
        </div>
        <div class="preview-diagnostic-card preview-queue-state">
          <span class="summary-label">后台任务</span>
          <strong>{{ previewQueueState.running || 0 }} 运行 / {{ previewQueueState.queued || 0 }} 排队</strong>
          <small>低占用队列状态</small>
        </div>
        <div class="preview-diagnostic-card preview-file-type-stats">
          <span class="summary-label">文件类型</span>
          <div v-if="Object.keys(previewFileTypeStats).length" class="preview-stat-tags">
            <el-tag v-for="(count, type) in previewFileTypeStats" :key="type" size="small" effect="plain">
              {{ type }} {{ count }}
            </el-tag>
          </div>
          <small v-else>暂无文件</small>
        </div>
        <div class="preview-diagnostic-card preview-largest-files">
          <span class="summary-label">占用排行</span>
          <div v-if="previewLargestFiles.length" class="preview-largest-list">
            <small v-for="item in previewLargestFiles" :key="item.file_id">
              {{ item.filename || item.file_id }} · {{ formatFileSize(item.storage_bytes || 0) }}
            </small>
          </div>
          <small v-else>暂无缓存占用</small>
        </div>
      </div>

      <div class="preview-ops-actions">
        <el-button type="primary" plain :loading="previewGenerateLoading" @click="generateMissingPreviews">
          生成缺失预览
        </el-button>
        <el-button type="warning" plain :loading="rebuildAllLoading" @click="rebuildAllPreviews">
          重建当前项目预览
        </el-button>
        <el-button type="danger" plain :loading="previewCleanupLoading" @click="cleanupFailedPreviews">
          清理失败/中断缓存
        </el-button>
        <span v-if="previewSummary.active" class="preview-polling-hint">正在自动刷新队列状态</span>
      </div>
    </el-card>

    <!-- 文件列表卡片 -->
    <el-card shadow="never" class="file-list-card">
      <template #header>
        <div class="card-header">
          <span>文件列表</span>
          <el-tag type="info">共 {{ files.length }} 个文件</el-tag>
        </div>
      </template>

      <div class="resource-toolbar">
        <div class="resource-breadcrumb">
          <el-button text :type="!currentFolderId ? 'primary' : 'default'" @click="openFolder('')">
            <el-icon><FolderOpened /></el-icon>
            根目录
          </el-button>
          <span v-if="currentFolder" class="folder-current-name">/ {{ currentFolder.name }}</span>
          <el-tag size="small" type="info">{{ resourceItems.length }} 个资源</el-tag>
        </div>
        <el-button type="primary" plain size="small" @click="openCreateFolderDialog">
          <el-icon><Plus /></el-icon>
          新建文件夹
        </el-button>
      </div>

      <div class="file-list-toolbar">
        <el-input
          v-model="fileSearchQuery"
          placeholder="搜索文件名、显示名、标签、分类"
          :prefix-icon="Search"
          clearable
          size="small"
          class="file-search-input"
        />
        <el-select
          v-model="fileTypeFilter"
          placeholder="文件类型"
          clearable
          size="small"
          class="file-type-filter"
        >
          <el-option label="PDF" value="pdf" />
          <el-option label="Word" value="docx" />
          <el-option label="Excel" value="xlsx" />
        </el-select>
        <el-select
          v-model="fileTagFilter"
          placeholder="标签"
          clearable
          multiple
          collapse-tags
          collapse-tags-tooltip
          size="small"
          class="file-tag-filter"
          @visible-change="onTagFilterOpen"
        >
          <el-option v-for="t in fileTagList" :key="t.id" :label="t.name" :value="t.id">
            <span class="tag-dot" :style="{background:t.color}"></span>
            {{ t.name }}
          </el-option>
        </el-select>
        <el-select
          v-model="fileCategoryFilter"
          placeholder="分类"
          clearable
          size="small"
          class="file-cat-filter"
          @visible-change="onCatFilterOpen"
        >
          <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select
          v-model="previewStatusFilter"
          placeholder="预览状态"
          clearable
          size="small"
          class="file-preview-filter"
        >
          <el-option label="生成中" value="active" />
          <el-option label="已就绪" value="ready" />
          <el-option label="失败/中断" value="problem" />
          <el-option label="缺失/不支持" value="missing" />
        </el-select>
        <span v-if="fileSearchLoading" class="file-search-hint is-loading">
          <el-icon><Loading /></el-icon>
          正在搜索
        </span>
        <span v-else-if="activeFileSearchKeyword" class="file-search-hint">
          已按相关性排序 · {{ filteredFiles.length }} 个结果
        </span>
      </div>

      <div v-if="!isMobile" class="file-table-scroll">
        <el-table
          :data="resourceItems"
          stripe
          style="width: 100%"
          row-key="id"
          :row-class-name="tableRowClassName"
          @row-click="handleResourceRowClick"
          @expand-change="onExpandChange"
          class="file-table"
        >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div v-if="row.type === 'file'" class="version-expand" v-loading="row._loadingVersions">
              <div class="version-expand-header">
                <span class="ve-title">版本列表 - {{ getFileDisplayName(row) }}</span>
              </div>
              <div v-if="row._versions && row._versions.length" class="version-list">
                <div
                  v-for="(v, vi) in row._versions"
                  :key="v.id"
                  class="version-row"
                  :class="{ 'version-row-latest': vi === 0 }"
                >
                  <span class="vr-num">V{{ v.version }}</span>
                  <span class="vr-hash">{{ v.file_hash?.slice(0, 8) || '-' }}</span>
                  <span class="vr-size">{{ formatFileSize(v.file_size) }}</span>
                  <span class="vr-time">{{ formatDate(v.created_at) }}</span>
                  <span class="vr-actions">
                    <el-button text size="small" @click="moveVersion(row, v, -1)" :disabled="vi === 0">
                      <el-icon><ArrowUp /></el-icon>
                    </el-button>
                    <el-button text size="small" @click="moveVersion(row, v, 1)" :disabled="vi === row._versions.length - 1">
                      <el-icon><ArrowDown /></el-icon>
                    </el-button>
                    <el-button text size="small" type="danger" @click="deleteVersion(row, v)" :disabled="row._versions.length <= 1">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </span>
                </div>
              </div>
              <el-empty v-else description="暂无版本" :image-size="40" />
            </div>
            <div v-else class="version-expand version-expand--empty">文件夹不提供版本历史</div>
          </template>
        </el-table-column>
        <el-table-column label="文件名" min-width="180">
          <template #default="{ row }">
            <div class="file-name-cell" :class="{ 'file-name-cell--folder': row.type === 'folder' || row.type === 'parent' }">
              <el-icon :size="20" :class="row.type === 'file' ? getFileTypeColor(row.file_type) : 'file-icon-folder'">
                <FolderOpened v-if="row.type === 'parent'" />
                <Folder v-else-if="row.type === 'folder'" />
                <component :is="getFileTypeIcon(row.file_type)" v-else />
              </el-icon>
              <div class="file-info">
                <span class="file-name">
                  <span v-if="row.type === 'file'">{{ getFileDisplayName(row) }}</span>
                  <span v-else :data-testid="row.type === 'folder' ? `resource-folder-item-${row.resourceId}` : undefined">{{ row.name }}</span>
                </span>
                <span class="file-path" v-if="row.type === 'file'">文件 ID：{{ shortFileId(row.id) }}</span>
                <span class="file-path" v-else-if="row.type === 'folder'">单击打开文件夹</span>
                <span class="file-path" v-else>返回根目录</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="82" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.type === 'folder'" size="small" type="warning">文件夹</el-tag>
            <el-tag v-else-if="row.type === 'parent'" size="small" type="info">上一级</el-tag>
            <el-tag v-else size="small" :type="getFileTypeTagType(row.file_type)">
              {{ row.file_type?.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="预览状态" width="180">
          <template #default="{ row }">
            <div v-if="row.type === 'file'" class="preview-status-cell">
              <div class="preview-status-line">
                <el-tag
                  size="small"
                  :type="getPreviewStatusTagType(getPreviewStatus(row).status)"
                  :effect="isPreviewActive(getPreviewStatus(row).status) ? 'dark' : 'light'"
                  :class="{ 'preview-status-active': isPreviewActive(getPreviewStatus(row).status) }"
                >
                  {{ getPreviewStatusLabel(getPreviewStatus(row).status) }}
                </el-tag>
                <el-tooltip
                  v-if="getPreviewStatus(row).error"
                  :content="getPreviewStatus(row).error"
                  placement="top"
                >
                  <el-icon class="preview-error-icon"><WarningFilled /></el-icon>
                </el-tooltip>
              </div>
              <el-progress
                v-if="isPreviewActive(getPreviewStatus(row).status)"
                :percentage="getPreviewStatus(row).progress || 0"
                :stroke-width="5"
                :show-text="false"
              />
              <el-tooltip
                :content="getPreviewTooltipText(getPreviewStatus(row))"
                placement="top"
              >
                <span class="preview-detail-text preview-detail-compact">
                  {{ getPreviewCompactText(getPreviewStatus(row)) }}
                </span>
              </el-tooltip>
            </div>
            <span v-else class="resource-cell-placeholder">—</span>
          </template>
        </el-table-column>
        <el-table-column label="信息" width="150">
          <template #default="{ row }">
            <div v-if="row.type === 'folder'" class="file-meta-cell">
              <span class="file-meta-main">{{ row.fileCount }} 个文件</span>
              <span class="file-meta-sub">单击进入文件夹</span>
            </div>
            <div v-else-if="row.type === 'parent'" class="file-meta-cell">
              <span class="file-meta-main">返回根目录</span>
              <span class="file-meta-sub">单击回到上一级</span>
            </div>
            <div v-else class="file-meta-cell">
              <span class="file-meta-main">
                <el-tag size="small" type="info">v{{ row.current_version || 1 }}</el-tag>
                <span>{{ formatFileSize(row.file_size) }}</span>
              </span>
              <span class="file-meta-sub">{{ formatDate(row.updated_at) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="232" align="center">
          <template #default="{ row }">
            <div v-if="row.type === 'folder'" class="action-buttons action-buttons-compact">
              <el-button text type="primary" size="small" @click.stop="openFolder(row.resourceId)">
                <el-icon><FolderOpened /></el-icon>
                打开
              </el-button>
              <el-dropdown trigger="click" @click.stop @command="(command) => handleFolderAction(command, row.folder)">
                <el-button text size="small" class="more-action-button" @click.stop>
                  <el-icon><MoreFilled /></el-icon>
                  更多
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="rename">重命名</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <div v-else-if="row.type === 'parent'" class="action-buttons action-buttons-compact">
              <el-button text type="primary" size="small" @click.stop="openFolder('')">
                <el-icon><FolderOpened /></el-icon>
                返回
              </el-button>
            </div>
            <div v-else class="action-buttons action-buttons-compact">
              <el-button text type="primary" size="small" @click.stop="handlePreview(row)">
                <el-icon><View /></el-icon>
                预览
              </el-button>
              <el-button text type="primary" size="small" class="action-btn-label" @click.stop="openShareDialog('file', row)" aria-label="分享文件">
                <el-icon><Share /></el-icon>
                <span class="btn-label">分享</span>
              </el-button>
              <el-button text size="small" @click.stop="openFileEditDialog(row)">
                <el-icon><PriceTag /></el-icon>
                设置
              </el-button>
              <el-dropdown trigger="click" @click.stop @command="(command) => handleFileRowAction(command, row)">
                <el-button text size="small" class="more-action-button" @click.stop>
                  <el-icon><MoreFilled /></el-icon>
                  更多
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="versions">
                      <el-icon><Edit /></el-icon>
                      版本管理
                    </el-dropdown-item>
                    <el-dropdown-item command="diff">
                      <el-icon><Sort /></el-icon>
                      Diff 对比
                    </el-dropdown-item>
                    <el-dropdown-item command="new-version">
                      <el-icon><Upload /></el-icon>
                      上传新版本
                    </el-dropdown-item>
                    <el-dropdown-item command="move">
                      <el-icon><FolderOpened /></el-icon>
                      移动到文件夹
                    </el-dropdown-item>
                    <el-dropdown-item command="share-access">
                      <el-icon><Share /></el-icon>
                      安全分享
                    </el-dropdown-item>
                    <el-dropdown-item command="rebuild-preview" :disabled="rebuildingIds.has(row.id)">
                      <el-icon><RefreshRight /></el-icon>
                      重建预览
                    </el-dropdown-item>
                    <el-dropdown-item command="delete" divided>
                      <el-icon><Delete /></el-icon>
                      删除文件
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
        </el-table>
      </div>

      <template v-else>
      <div class="resource-mobile-shell" data-testid="admin-mobile-resource-shell">
        <div class="resource-mobile-shell__head">
          <div>
            <span class="resource-mobile-shell__eyebrow">资源区</span>
            <h3 class="resource-mobile-shell__title">{{ currentFolder?.name || '全部资源' }}</h3>
          </div>
          <el-tag size="small" type="info" effect="plain">{{ resourceItems.length }} 个资源</el-tag>
        </div>
        <details class="resource-mobile-shell__details">
          <summary data-testid="admin-mobile-resource-summary">筛选与说明</summary>
          <p>文件夹与文件已合并展示，点击文件夹单行即可进入。</p>
        </details>
      </div>

      <FileListCards
        :items="resourceItems"
        variant="admin"
        test-id="admin-mobile-file-list"
      >
        <template #icon="{ item }">
          <div class="file-list-card__icon file-list-card__icon--admin" :class="{ 'file-list-card__icon--folder': item.type === 'folder' || item.type === 'parent' }">
            <el-icon :size="18">
              <FolderOpened v-if="item.type === 'parent'" />
              <Folder v-else-if="item.type === 'folder'" />
              <component :is="getFileTypeIcon(item.file_type)" v-else />
            </el-icon>
          </div>
        </template>
        <template #title="{ item }">
          <span v-if="item.type === 'folder'" :data-testid="`resource-folder-item-${item.resourceId}`">{{ item.name }}</span>
          <span v-else-if="item.type === 'parent'">返回上一级</span>
          <span v-else>{{ getFileDisplayName(item) }}</span>
        </template>
        <template #subtitle="{ item }">
          <template v-if="item.type === 'folder'">
            文件夹 · {{ item.fileCount }} 个文件
          </template>
          <template v-else-if="item.type === 'parent'">
            回到根目录
          </template>
          <template v-else>
            {{ item.file_type?.toUpperCase() || 'FILE' }} · {{ formatFileSize(item.file_size || 0) }}
          </template>
        </template>
        <template #badges="{ item }">
          <el-tag v-if="item.type === 'folder'" size="small" type="warning" effect="plain">
            文件夹
          </el-tag>
          <template v-else-if="item.type !== 'parent'">
            <el-tag size="small" :type="getFileTypeTagType(item.file_type)">
              {{ item.file_type?.toUpperCase() }}
            </el-tag>
            <el-tag size="small" type="info" effect="plain">v{{ item.current_version || 1 }}</el-tag>
            <el-tag
              size="small"
              :type="getPreviewStatusTagType(getPreviewStatus(item).status)"
              effect="plain"
            >
              {{ getPreviewStatusLabel(getPreviewStatus(item).status) }}
            </el-tag>
          </template>
        </template>
        <template #meta="{ item }">
          <template v-if="item.type === 'folder'">
            <span>点击进入文件夹</span>
          </template>
          <template v-else-if="item.type === 'parent'">
            <span>点击返回根目录</span>
          </template>
          <template v-else>
            <span>{{ formatDate(item.updated_at) }}</span>
            <span>·</span>
            <span>{{ shortFileId(item.id) }}</span>
          </template>
        </template>
        <template #summary="{ item }">
          <span v-if="item.type === 'folder'" class="mobile-preview-summary">与文件同区域展示</span>
          <span v-else-if="item.type !== 'parent'" class="mobile-preview-summary">{{ getPreviewCompactText(getPreviewStatus(item)) }}</span>
        </template>
        <template #actions="{ item }">
          <template v-if="item.type === 'folder'">
            <el-button text type="primary" size="small" @click.stop="openFolder(item.resourceId)" class="action-btn">
              <el-icon><FolderOpened /></el-icon>
              打开
            </el-button>
            <el-dropdown trigger="click" @command="(command) => handleFolderAction(command, item.folder)">
              <el-button text size="small" class="action-btn">
                <el-icon><MoreFilled /></el-icon>
                更多
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">重命名</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else-if="item.type === 'parent'">
            <el-button text type="primary" size="small" @click.stop="openFolder('')" class="action-btn">
              <el-icon><FolderOpened /></el-icon>
              返回
            </el-button>
          </template>
          <template v-else>
            <el-button text type="primary" size="small" @click.stop="handlePreview(item)" class="action-btn">
              <el-icon><View /></el-icon>
              预览
            </el-button>
            <el-button text type="primary" size="small" @click.stop="openShareDialog('file', item)" class="action-btn">
              <el-icon><Share /></el-icon>
              分享
            </el-button>
            <el-dropdown trigger="click" @command="(command) => handleFileRowAction(command, item)">
              <el-button text size="small" class="action-btn">
                <el-icon><MoreFilled /></el-icon>
                更多
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="versions">
                    <el-icon><Edit /></el-icon>
                    版本管理
                  </el-dropdown-item>
                  <el-dropdown-item command="diff">
                    <el-icon><Sort /></el-icon>
                    Diff 对比
                  </el-dropdown-item>
                  <el-dropdown-item command="new-version">
                    <el-icon><Upload /></el-icon>
                    上传新版本
                  </el-dropdown-item>
                  <el-dropdown-item command="move">
                    <el-icon><FolderOpened /></el-icon>
                    移动到文件夹
                  </el-dropdown-item>
                  <el-dropdown-item command="share-access">
                    <el-icon><Share /></el-icon>
                    安全分享
                  </el-dropdown-item>
                  <el-dropdown-item command="rebuild-preview" :disabled="rebuildingIds.has(item.id)">
                    <el-icon><RefreshRight /></el-icon>
                    重建预览
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>
                    <el-icon><Delete /></el-icon>
                    删除文件
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </template>
      </FileListCards>
      </template>

      <!-- 批量操作栏 -->
      <div class="batch-bar" v-if="filteredFiles.length">
        <el-button type="warning" @click="rebuildAllPreviews" :loading="rebuildAllLoading">
          <el-icon><RefreshRight /></el-icon>
          全部重建预览 ({{ filteredFiles.filter(f => ['docx','doc','pdf'].includes(f.file_type)).length }} 个文档)
        </el-button>
      </div>

      <el-empty v-if="!loading && resourceItems.length === 0" :description="fileEmptyDescription">
        <el-button type="primary" @click="goToUpload">上传文件</el-button>
      </el-empty>
    </el-card>

    <!-- 文件预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      :title="getPreviewDialogTitle(previewFile, previewVersion)"
      width="min(1280px, calc(100vw - 64px))"
      top="5vh"
      destroy-on-close
      append-to-body
      modal-class="preview-dialog-mask"
      class="preview-dialog"
      @closed="onPreviewDialogClosed"
    >
      <div class="preview-container">
        <div v-if="previewLoading" class="preview-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载预览中...</span>
        </div>
        <div v-else-if="previewError" class="preview-error">
          <el-icon :size="48"><WarningFilled /></el-icon>
          <p>{{ previewError }}</p>
          <el-button type="primary" @click="loadPreview">重试</el-button>
        </div>
        <div v-else class="preview-content">
          <div class="preview-header">
            <span>版本: v{{ previewVersion }}</span>
            <el-select v-model="previewVersion" size="small" @change="loadPreview">
              <el-option
                v-for="v in fileVersions"
                :key="v"
                :label="`版本 ${v}`"
                :value="v"
              />
            </el-select>
          </div>
          <div class="preview-body">
            <div v-if="previewIsNativeVideo" class="preview-video-container">
              <video
                data-testid="preview-video-player"
                class="preview-video-player"
                :src="previewUrl"
                controls
                playsinline
                preload="metadata"
              />
            </div>
            <div v-else-if="previewFrameVisible" class="preview-iframe-container">
              <iframe
                v-if="previewHtml"
                :srcdoc="previewHtml"
                :class="['preview-iframe', { 'preview-iframe--native-html': previewIsNativeHtml }]"
                :sandbox="previewFrameSandbox"
              ></iframe>
              <iframe
                v-else
                :src="previewUrl"
                :class="['preview-iframe', { 'preview-iframe--native-html': previewIsNativeHtml }]"
                :sandbox="previewFrameSandbox"
              ></iframe>
            </div>
            <div v-else class="preview-placeholder">
              <el-icon :size="64"><Document /></el-icon>
              <p>{{ getPreviewDialogTitle(previewFile, previewVersion) }}</p>
              <el-button type="primary" @click="downloadFile(previewFile)">
                <el-icon><Download /></el-icon>
                下载查看
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 版本管理对话框 -->
    <el-dialog
      v-model="versionTimelineVisible"
      :title="'版本管理 - ' + getFileDisplayName(manageFile)"
      width="680px"
      v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"
      class="admin-viewport-dialog"
      destroy-on-close
      @opened="fetchRealVersions"
    >
      <div v-loading="categoryLoading" class="version-manage">
        <div v-if="realVersions.length" class="vm-list">
          <div v-for="(v, vi) in realVersions" :key="v.id" class="vm-row" :class="{ 'vm-latest': vi === 0 }">
            <span class="vm-num"><strong>V{{ v.version }}</strong></span>
            <span class="vm-meta">{{ formatFileSize(v.file_size) }} · {{ v.file_hash?.slice(0,8) || '-' }}</span>
            <span class="vm-time">{{ formatDate(v.created_at) }}</span>
            <span class="vm-actions">
              <el-button size="small" text @click="moveVersionApi(vi, -1)" :disabled="vi === 0"><el-icon><ArrowUp /></el-icon></el-button>
              <el-button size="small" text @click="moveVersionApi(vi, 1)" :disabled="vi === realVersions.length - 1"><el-icon><ArrowDown /></el-icon></el-button>
              <el-button size="small" text type="danger" @click="deleteVersionApi(vi)" :disabled="realVersions.length <= 1"><el-icon><Delete /></el-icon></el-button>
            </span>
          </div>
        </div>
        <el-empty v-else description="暂无版本" />
      </div>
      <template #footer>
        <el-button @click="versionTimelineVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 文件设置对话框 -->
    <el-dialog
      v-model="fileEditVisible"
      title="文件设置"
      width="560px"
      v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"
      class="admin-viewport-dialog"
      destroy-on-close
      @opened="loadFileEditData"
    >
      <el-form label-position="top" class="file-edit-form">
        <el-form-item label="显示名称">
          <el-input v-model="editForm.display_name" placeholder="可选，不填则使用原文件名" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="文档描述..." />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="editForm.category_id" placeholder="选择分类" clearable style="width:100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id">
              <span :style="{display:'inline-block',width:'10px',height:'10px',borderRadius:'50%',background:c.color,marginRight:'6px'}"></span>
              {{ c.name }}
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="editForm.tag_ids" multiple placeholder="选择标签" style="width:100%">
            <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id">
              <span :style="{display:'inline-block',width:'8px',height:'8px',borderRadius:'2px',background:t.color,marginRight:'6px'}"></span>
              {{ t.name }}
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="封面图片">
          <div v-if="editForm.cover_image" class="cover-preview">
            <img :src="editForm.cover_image" alt="封面" style="max-height:120px;border-radius:8px" />
            <el-button size="small" type="danger" text @click="editForm.cover_image = ''">移除封面</el-button>
          </div>
          <el-upload
            v-else
            :show-file-list="false"
            :before-upload="handleCoverUpload"
            accept="image/*"
          >
            <el-button size="small">
              <el-icon><Upload /></el-icon> 上传封面
            </el-button>
          </el-upload>
        </el-form-item>
        <div class="share-access-section">
          <div class="share-access-section__title">公开浏览权限</div>
          <div class="share-field-note">控制公开浏览时的预览、变更、版本、下载以及密码 / 用户组访问。</div>
          <el-form-item label="公开方式">
            <el-select v-model="fileAccessForm.visibility" style="width: 100%">
              <el-option
                v-for="option in fileAccessVisibilityOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <div class="share-access-grid">
            <el-form-item label="允许预览">
              <el-switch v-model="fileAccessForm.allow_preview" active-text="允许" inactive-text="禁止" />
            </el-form-item>
            <el-form-item label="允许下载">
              <el-switch v-model="fileAccessForm.allow_download" active-text="允许" inactive-text="禁止" />
            </el-form-item>
            <el-form-item label="允许变更 Diff">
              <el-switch v-model="fileAccessForm.allow_diff" active-text="允许" inactive-text="禁止" />
            </el-form-item>
            <el-form-item label="允许版本历史">
              <el-switch v-model="fileAccessForm.allow_versions" active-text="允许" inactive-text="禁止" />
            </el-form-item>
          </div>
          <el-form-item label="访问密码">
            <el-input
              v-model="fileAccessForm.password"
              type="password"
              show-password
              :disabled="fileAccessForm.clear_password"
              :placeholder="fileAccessForm.has_password ? '留空则保留当前密码' : '留空则不启用新密码'"
            />
          </el-form-item>
          <el-form-item label="清除现有密码">
            <el-switch
              v-model="fileAccessForm.clear_password"
              :disabled="Boolean(fileAccessForm.password)"
              active-text="清除"
              inactive-text="保留"
            />
          </el-form-item>
          <el-form-item label="密码提示">
            <el-input v-model="fileAccessForm.password_hint" placeholder="例如：部门简称、项目代号" />
          </el-form-item>
          <el-form-item label="用户组访问">
            <el-select
              v-model="fileAccessForm.group_codes"
              multiple
              clearable
              collapse-tags
              collapse-tags-tooltip
              style="width: 100%"
            >
              <el-option
                v-for="group in accessGroups"
                :key="group.code"
                :label="group.name || group.code"
                :value="group.code"
              />
            </el-select>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="loadCategories">刷新分类标签</el-button>
        <el-button type="primary" @click="saveFileEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="projectAccessVisible"
      title="公开浏览权限"
      width="560px"
      v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"
      class="admin-viewport-dialog"
      destroy-on-close
    >
      <el-form label-position="top" class="file-edit-form">
        <div class="share-access-section">
          <div class="share-access-section__title">项目级公开浏览</div>
          <div class="share-field-note">项目公开页、分享页壳和资源访问都会遵循这里的权限控制。</div>
          <el-form-item label="公开方式">
            <el-select v-model="projectAccessForm.visibility" style="width: 100%">
              <el-option
                v-for="option in projectAccessVisibilityOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <div class="share-access-grid">
            <el-form-item label="允许预览">
              <el-switch v-model="projectAccessForm.allow_preview" active-text="允许" inactive-text="禁止" />
            </el-form-item>
            <el-form-item label="允许下载">
              <el-switch v-model="projectAccessForm.allow_download" active-text="允许" inactive-text="禁止" />
            </el-form-item>
            <el-form-item label="允许变更 Diff">
              <el-switch v-model="projectAccessForm.allow_diff" active-text="允许" inactive-text="禁止" />
            </el-form-item>
            <el-form-item label="允许版本历史">
              <el-switch v-model="projectAccessForm.allow_versions" active-text="允许" inactive-text="禁止" />
            </el-form-item>
          </div>
          <el-form-item label="访问密码">
            <el-input
              v-model="projectAccessForm.password"
              type="password"
              show-password
              :disabled="projectAccessForm.clear_password"
              :placeholder="projectAccessForm.has_password ? '留空则保留当前密码' : '留空则不启用新密码'"
            />
          </el-form-item>
          <el-form-item label="清除现有密码">
            <el-switch
              v-model="projectAccessForm.clear_password"
              :disabled="Boolean(projectAccessForm.password)"
              active-text="清除"
              inactive-text="保留"
            />
          </el-form-item>
          <el-form-item label="密码提示">
            <el-input v-model="projectAccessForm.password_hint" placeholder="例如：项目代号、部门简称" />
          </el-form-item>
          <el-form-item label="用户组访问">
            <el-select
              v-model="projectAccessForm.group_codes"
              multiple
              clearable
              collapse-tags
              collapse-tags-tooltip
              style="width: 100%"
            >
              <el-option
                v-for="group in accessGroups"
                :key="group.code"
                :label="group.name || group.code"
                :value="group.code"
              />
            </el-select>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="projectAccessVisible = false">取消</el-button>
        <el-button type="primary" @click="saveProjectAccessPolicy">保存</el-button>
      </template>
    </el-dialog>

    <!-- 文件夹编辑对话框 -->
    <el-dialog
      v-model="folderDialogVisible"
      :title="editingFolder ? '重命名文件夹' : '新建文件夹'"
      width="420px"
      v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"
      class="admin-viewport-dialog"
      destroy-on-close
    >
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="文件夹名称" required>
          <el-input
            v-model="folderForm.name"
            maxlength="100"
            show-word-limit
            placeholder="例如：合同、图纸、阶段一"
            @keyup.enter="saveFolder"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="folderDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="folderSaving" @click="saveFolder">保存</el-button>
      </template>
    </el-dialog>

    <!-- 移动文件对话框 -->
    <el-dialog
      v-model="moveFileDialogVisible"
      title="移动到文件夹"
      width="460px"
      v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"
      class="admin-viewport-dialog"
      destroy-on-close
    >
      <div class="move-file-summary">
        <el-icon><Document /></el-icon>
        <span>{{ getFileDisplayName(movingFile) }}</span>
      </div>
      <el-radio-group v-model="targetFolderId" class="move-folder-list">
        <el-radio-button label="">根目录</el-radio-button>
        <el-radio-button
          v-for="folder in folders"
          :key="folder.id"
          :label="folder.id"
        >
          {{ folder.name }}
        </el-radio-button>
      </el-radio-group>
      <template #footer>
        <el-button @click="moveFileDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="moveSaving" @click="moveSelectedFile">移动</el-button>
      </template>
    </el-dialog>

    <!-- 分享令牌对话框 -->
    <el-dialog
      v-model="shareDialogVisible"
      :title="shareDialogTitle"
      width="560px"
      v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"
      class="admin-viewport-dialog"
      destroy-on-close
    >
      <el-form v-loading="shareDialogLoading" label-position="top" class="share-token-form">
        <el-form-item label="分享名称">
          <el-input v-model="shareForm.name" placeholder="用于管理端识别该分享令牌" />
        </el-form-item>
        <div v-if="editingShareToken" class="share-dialog-existing-note">
          当前正在编辑已有分享：{{ editingShareToken.token_preview || editingShareToken.token || '已存在链接' }}
        </div>
        <div class="share-limit-grid">
          <el-form-item label="最大浏览次数">
            <el-input-number v-model="shareForm.max_views" :min="0" :step="1" />
          </el-form-item>
          <el-form-item label="最大下载次数">
            <el-input-number v-model="shareForm.max_downloads" :min="0" :step="1" />
          </el-form-item>
        </div>
        <el-form-item label="允许下载">
          <el-switch v-model="shareForm.allow_download" active-text="允许" inactive-text="禁止" />
        </el-form-item>
        <el-form-item label="过期时间">
          <el-date-picker
            v-model="shareForm.expires_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="不设置则长期有效"
            style="width: 100%"
          />
        </el-form-item>
        <div class="share-access-section">
          <div class="share-access-section__title">访问与权限控制</div>
          <p class="share-access-section__summary">分享权限仅作用于分享链接，不继承公开浏览权限。</p>
          <div class="share-access-grid">
            <el-form-item label="需要登录">
              <el-switch v-model="shareForm.require_login" active-text="是" inactive-text="否" />
            </el-form-item>
            <el-form-item label="允许预览">
              <el-switch v-model="shareForm.allow_preview" active-text="允许" inactive-text="禁用" />
            </el-form-item>
            <el-form-item label="允许 Diff">
              <el-switch v-model="shareForm.allow_diff" active-text="允许" inactive-text="禁用" />
            </el-form-item>
            <el-form-item label="允许版本">
              <el-switch v-model="shareForm.allow_versions" active-text="允许" inactive-text="禁用" />
            </el-form-item>
          </div>
          <el-form-item label="访问密码">
            <el-input
              v-model="shareForm.password"
              type="password"
              show-password
              :disabled="shareForm.clear_password"
              :placeholder="editingShareToken ? '留空则保留现有密码' : '留空则不启用密码'"
            />
          </el-form-item>
          <el-form-item v-if="editingShareToken" label="清除现有密码">
            <el-switch
              v-model="shareForm.clear_password"
              :disabled="Boolean(shareForm.password)"
              active-text="清除"
              inactive-text="保留"
            />
            <div class="share-field-note">不输入新密码时，可直接清除当前访问密码。</div>
          </el-form-item>
          <el-form-item label="密码提示">
            <el-input
              v-model="shareForm.password_hint"
              placeholder="例如：项目简称、部门代号"
            />
          </el-form-item>
        </div>
        <div class="share-dialog-hint">
          {{ shareDialogHint }}
        </div>
      </el-form>
      <template #footer>
        <el-button @click="closeShareDialog">取消</el-button>
        <el-button type="primary" :loading="shareSaving" @click="createShareLink">{{ shareDialogPrimaryText }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, ArrowUp, ArrowDown, Upload, Search, View, Sort, Delete,
  Document, Download, WarningFilled,
  Loading, Edit, PriceTag, Share, RefreshRight, MoreFilled,
  Folder, FolderOpened, Plus, Lock
} from '@element-plus/icons-vue'
import {
  getProject,
  getProjectFiles,
  getProjectFolders,
  createProjectFolder,
  renameProjectFolder,
  deleteProjectFolder,
  moveProjectFileToFolder,
} from '@/api/project'
import {
  deleteFile,
  getPreviewStatuses,
  enqueuePreviewGeneration,
  clearPreviewCache,
} from '@/api/file'
import client from '@/api/client'
import { createShareToken, listShareTokens, updateShareToken } from '@/api/share'
import {
  getResourceAccessPolicy,
  listAccessGroups,
  updateResourceAccessPolicy,
} from '@/api/accessControl'
import { resolveCoverUrl } from '@/utils/cover'
import { formatDate, formatFileSize, getFileTypeIcon, copyToClipboard } from '@/utils'
import { buildClientPreviewManifest } from '@/utils/filePreview'
import { buildAuthenticatedPreviewUrl, buildPreviewSrcdoc, shouldShowPreviewFrame } from '@/utils/preview'
import {
  buildShareUrl,
  indexLatestShareTokensByResource,
  isPreviewActiveStatus,
  mergeCreatedShareToken,
  normalizePreviewStatusRow,
  previewStatusLabel,
  shareResourceKey,
} from '@/utils/previewManagement'
import { getVersionPreviewCacheKey, hasSameVersionPreviewRefresh } from '@/utils/versionHistory'
import FileListCards from '@/components/file/FileListCards.vue'
import { useResponsive } from '@/composables/useResponsive'
import PageHeader from '@/components/common/PageHeader.vue'
import { ADMIN_VIEWPORT_DIALOG_PROPS } from '@/utils/adminDialog'
import { buildShareHomePath } from '@/utils/shareRoute'
import { buildShareTokenFormState, buildShareTokenMutationPayload } from '@/utils/shareTokenForm'
import {
  buildResourceAccessFormState,
  buildResourceAccessMutationPayload,
  getResourceAccessVisibilityOptions,
} from '@/utils/resourceAccessForm'

const route = useRoute()
const router = useRouter()

function resolveShareFormDefaults(scope = 'project', file = null, options = {}) {
  const isFile = scope === 'file' && file
  return {
    name: isFile ? `分享文件：${getFileDisplayName(file)}` : `分享项目：${project.value?.name || ''}`,
    resource_type: isFile ? 'file' : 'project',
    resource_id: isFile ? file.id : project.value?.id,
    policy_mode: options.policyMode,
  }
}

function buildShareDialogForm(scope = 'project', file = null, options = {}) {
  return buildShareTokenFormState({
    token: options.existingToken || null,
    defaults: resolveShareFormDefaults(scope, file, options),
  })
}

const project = ref(null)
const files = ref([])
const loading = ref(false)

const rebuildingIds = ref(new Set())
const rebuildAllLoading = ref(false)
const previewGenerateLoading = ref(false)
const previewOpsLoading = ref(false)
const previewCleanupLoading = ref(false)
const previewRows = ref([])
const previewSummary = ref({})
const previewStorageBreakdown = computed(() => previewSummary.value.storage_breakdown || {})
const previewLargestFiles = computed(() => previewSummary.value.largest_files || [])
const previewFileTypeStats = computed(() => previewSummary.value.by_file_type || {})
const previewQueueState = computed(() => previewSummary.value.queue_state || { queued: 0, running: 0 })
const previewPollTimer = ref(null)
const previewVersionPollTimer = ref(null)

const fileSearchQuery = ref('')
const { isMobile } = useResponsive()
const fileSearchLoading = ref(false)
const fileSearchTimer = ref(null)
const activeFileSearchKeyword = ref('')
let latestFileSearchRequestId = 0
const fileTypeFilter = ref('')
const fileTagFilter = ref([])
const fileCategoryFilter = ref('')
const previewStatusFilter = ref('')
const fileTagList = ref([])
const folders = ref([])
const currentFolderId = ref(String(route.query.folder_id || ''))
const folderDialogVisible = ref(false)
const folderForm = ref({ name: '' })
const editingFolder = ref(null)
const folderSaving = ref(false)
const moveFileDialogVisible = ref(false)
const movingFile = ref(null)
const targetFolderId = ref('')
const moveSaving = ref(false)
const shareDialogVisible = ref(false)
const shareDialogLoading = ref(false)
const shareSaving = ref(false)
const shareTarget = ref(null)
const editingShareToken = ref(null)
const shareForm = ref(buildShareDialogForm())
const shareTokensByResource = ref({})
const accessGroups = ref([])
const accessGroupsLoaded = ref(false)
const projectAccessVisible = ref(false)
const projectAccessForm = ref(buildResourceAccessFormState({
  scope: 'project',
  defaultVisibility: 'public',
}))
const fileAccessForm = ref(buildResourceAccessFormState({
  scope: 'file',
  defaultVisibility: 'inherit',
}))
const projectAccessVisibilityOptions = getResourceAccessVisibilityOptions('project')
const fileAccessVisibilityOptions = getResourceAccessVisibilityOptions('file')
const shareDialogTitle = computed(() => {
  const targetLabel = shareForm.value.resource_type === 'file' ? '文件' : '项目'
  return editingShareToken.value ? `编辑${targetLabel}分享` : `创建${targetLabel}分享链接`
})
const shareDialogPrimaryText = computed(() => (
  editingShareToken.value ? '保存并复制链接' : '创建并复制'
))
const shareDialogHint = computed(() => (
  editingShareToken.value
    ? '当前资源已存在分享，保存后将直接更新当前分享权限，并保留原链接地址。'
    : '创建后会自动复制链接，并同步到当前项目/文件的最新分享记录。'
))

// 预览相关
const previewDialogVisible = ref(false)
const previewFile = ref(null)
const previewUrl = ref('')
const previewHtml = ref('')
const previewLoading = ref(false)
const previewError = ref('')
const previewVersion = ref(1)
const fileVersions = ref([])
const previewCacheKey = ref('')
const previewVersionRefreshToken = ref('')
const previewUpdateNoticeKey = ref('')
const previewFrameVisible = computed(() => shouldShowPreviewFrame(previewHtml.value, previewUrl.value))
const previewManifestType = computed(() => {
  if (!previewFile.value) return ''
  return previewFile.value?.preview_manifest?.type || buildClientPreviewManifest(previewFile.value).type
})
const previewIsNativeVideo = computed(() => previewManifestType.value === 'video_native')
const previewIsNativeHtml = computed(() => ['html_native', 'html_runtime'].includes(previewManifestType.value))
const previewFrameSandbox = computed(() => (previewIsNativeHtml.value ? null : 'allow-same-origin'))
const versionTimelineVisible = ref(false)
const manageFile = ref(null)
const realVersions = ref([])
const categories = ref([])
const tags = ref([])
const categoryLoading = ref(false)
const expandedRows = ref([])

const breadcrumbs = computed(() => [
  { title: '项目管理', path: '/admin/projects' },
  { title: project.value?.name || '项目详情' }
])

const currentFolder = computed(() =>
  folders.value.find((folder) => folder.id === currentFolderId.value) || null
)

const filteredFiles = computed(() => {
  let result = files.value.filter((file) => (file.folder_id || '') === (currentFolderId.value || ''))
  if (fileTypeFilter.value) {
    result = result.filter(f => f.file_type === fileTypeFilter.value)
  }
  if (fileTagFilter.value.length) {
    result = result.filter(f => {
      const fileTagIds = (f.tags || []).map(t => t.id || t)
      return fileTagFilter.value.some(tid => fileTagIds.includes(tid))
    })
  }
  if (fileCategoryFilter.value) {
    result = result.filter(f => f.category_id === fileCategoryFilter.value)
  }
  if (previewStatusFilter.value) {
    result = result.filter((file) => matchesPreviewStatusFilter(file))
  }
  return result
})

const hasLocalFileFilters = computed(() => (
  Boolean(fileTypeFilter.value)
  || Boolean(fileTagFilter.value.length)
  || Boolean(fileCategoryFilter.value)
  || Boolean(previewStatusFilter.value)
))

const fileEmptyDescription = computed(() => (
  activeFileSearchKeyword.value
    ? '没有匹配文件，换个关键词试试'
    : (hasLocalFileFilters.value ? '没有符合筛选条件的文件' : '暂无文件，点击上方按钮上传')
))

const visibleFolders = computed(() => {
  if (getFileSearchKeyword()) return []
  if (hasLocalFileFilters.value) return []
  if (currentFolderId.value) return []
  return folders.value
})

const parentResourceItem = computed(() => {
  if (!currentFolderId.value) return null
  return {
    id: 'parent-folder-row',
    resourceId: '',
    type: 'parent',
    name: '..',
  }
})

const resourceItems = computed(() => {
  const items = []
  if (parentResourceItem.value) items.push(parentResourceItem.value)
  items.push(
    ...visibleFolders.value.map((folder) => ({
      id: `folder-${folder.id}`,
      resourceId: folder.id,
      type: 'folder',
      name: folder.name || '未命名文件夹',
      fileCount: getFolderFileCount(folder.id),
      folder,
    })),
  )
  items.push(
    ...filteredFiles.value.map((file) => ({
      ...file,
      resourceId: file.id,
      type: 'file',
    })),
  )
  return items
})

const previewByFileId = computed(() => {
  const map = {}
  previewRows.value.forEach((row) => {
    map[row.file_id] = row
  })
  return map
})

function getPreviewStatus(file) {
  return normalizePreviewStatusRow(file, previewByFileId.value[file.id])
}

function matchesPreviewStatusFilter(file) {
  const status = getPreviewStatus(file)?.status || 'missing'
  switch (previewStatusFilter.value) {
    case 'active':
      return isPreviewActive(status)
    case 'ready':
      return status === 'ready'
    case 'problem':
      return ['failed', 'interrupted'].includes(status)
    case 'missing':
      return ['missing', 'unsupported'].includes(status)
    default:
      return true
  }
}

function getPreviewableFiles() {
  return filteredFiles.value.filter((file) => ['docx', 'doc', 'pdf'].includes(file.file_type))
}

function isPreviewActive(status) {
  return isPreviewActiveStatus(status)
}

function getPreviewStatusLabel(status) {
  return previewStatusLabel(status)
}

function getPreviewDetailText(status) {
  if (!status) return ''
  const parts = []
  if (status.stage) parts.push(status.stage)
  if (status.page_count) {
    const rendered = status.rendered_pages ?? 0
    parts.push(`${rendered}/${status.page_count}页`)
  }
  if (status.source_hash_short) parts.push(`源 ${status.source_hash_short}`)
  if (status.pdf_hash_short) parts.push(`PDF ${status.pdf_hash_short}`)
  return parts.join(' · ')
}

function getPreviewCacheText(status) {
  if (!status?.storage_bytes) return '无缓存'
  const parts = [`缓存 ${formatFileSize(status.storage_bytes)}`]
  if (status.pdf_bytes) parts.push(`PDF ${formatFileSize(status.pdf_bytes)}`)
  if (status.image_bytes) parts.push(`图片 ${formatFileSize(status.image_bytes)}`)
  return parts.join(' / ')
}

function getPreviewUpdatedText(status) {
  const time = status?.finished_at || status?.updated_at || status?.started_at || status?.queued_at
  return time ? `更新 ${formatDate(time)}` : ''
}

function getPreviewCompactText(status = {}) {
  if (!status || status.status === 'missing') return '未生成'
  if (isPreviewActive(status.status)) return `${status.progress || 0}%`
  if (status.status === 'ready') {
    const pages = status.page_count || status.pages || status.image_count || 0
    const pdfSize = status.pdf_bytes || status.pdf_size || status.preview_pdf_size || 0
    const pageText = pages ? `${pages}页` : '已生成'
    return pdfSize ? `${pageText} · ${formatFileSize(pdfSize)}` : pageText
  }
  if (status.status === 'unsupported') return '不支持'
  if (status.error) return '查看错误'
  return getPreviewStatusLabel(status.status)
}

function getPreviewTooltipText(status = {}) {
  return [
    getPreviewDetailText(status),
    getPreviewCacheText(status),
    getPreviewUpdatedText(status),
    status?.error ? `错误：${status.error}` : '',
  ].filter(Boolean).join('\n')
}

function getPreviewStatusTagType(status) {
  const map = {
    ready: 'success',
    queued: 'warning',
    pdf_generating: 'warning',
    pdf_ready: 'warning',
    images_generating: 'warning',
    failed: 'danger',
    interrupted: 'danger',
    unsupported: 'info',
    missing: 'info',
  }
  return map[status] || 'info'
}

function startPreviewPollingIfNeeded() {
  const active = previewRows.value.some((row) => isPreviewActive(row.status))
  if (!active) {
    stopPreviewPolling()
    return
  }
  if (previewPollTimer.value) return
  previewPollTimer.value = window.setInterval(() => {
    fetchPreviewStatuses({ silent: true })
  }, 2000)
}

function stopPreviewPolling() {
  if (previewPollTimer.value) {
    window.clearInterval(previewPollTimer.value)
    previewPollTimer.value = null
  }
}

function stopPreviewVersionPolling() {
  if (previewVersionPollTimer.value) {
    window.clearInterval(previewVersionPollTimer.value)
    previewVersionPollTimer.value = null
  }
}

function stopFileSearchDebounce() {
  if (fileSearchTimer.value) {
    window.clearTimeout(fileSearchTimer.value)
    fileSearchTimer.value = null
  }
}

function getFileSearchKeyword() {
  return String(fileSearchQuery.value || '').trim()
}

async function searchProjectFiles(options = {}) {
  stopFileSearchDebounce()
  const keyword = getFileSearchKeyword()
  const requestId = ++latestFileSearchRequestId
  if (!options.silent) fileSearchLoading.value = true
  try {
    const params = {
      ...(keyword ? { keyword } : {}),
      ...(currentFolderId.value ? { folder_id: currentFolderId.value } : {}),
    }
    const data = await getProjectFiles(route.params.id, params)
    if (requestId !== latestFileSearchRequestId) return
    const nextFiles = Array.isArray(data?.files) ? data.files : (Array.isArray(data) ? data : [])
    files.value = mergeProjectFilesWithExisting(nextFiles)
    activeFileSearchKeyword.value = keyword
  } catch (err) {
    if (requestId === latestFileSearchRequestId && !options.silent) {
      ElMessage.error(err.message || '搜索文件失败')
    }
  } finally {
    if (requestId === latestFileSearchRequestId && !options.silent) {
      fileSearchLoading.value = false
    }
  }
}

function scheduleProjectFileSearch() {
  stopFileSearchDebounce()
  fileSearchTimer.value = window.setTimeout(() => {
    fileSearchTimer.value = null
    searchProjectFiles()
  }, 300)
}

async function fetchPreviewStatuses(options = {}) {
  if (!options.silent) previewOpsLoading.value = true
  try {
    const data = await getPreviewStatuses({ project_id: route.params.id })
    previewRows.value = data.files || []
    previewSummary.value = data.summary || {}
    startPreviewPollingIfNeeded()
  } catch (err) {
    if (!options.silent) {
      ElMessage.error(err.message || '预览状态加载失败')
    }
  } finally {
    if (!options.silent) previewOpsLoading.value = false
  }
}

function onTagFilterOpen(visible) {
  if (visible && fileTagList.value.length === 0) {
    client.get('/tags').then(d => { fileTagList.value = d || [] }).catch(() => {})
  }
}

function onCatFilterOpen(visible) {
  if (visible && categories.value.length === 0) {
    client.get('/categories').then(d => { categories.value = d || [] }).catch(() => {})
  }
}

function getFileTypeTagType(type) {
  const map = { pdf: 'danger', docx: 'primary', doc: 'primary', xlsx: 'success', xls: 'success' }
  return map[type] || 'info'
}

function getFileTypeColor(type) {
  const map = { pdf: 'file-icon-pdf', docx: 'file-icon-docx', doc: 'file-icon-docx', xlsx: 'file-icon-xlsx', xls: 'file-icon-xlsx' }
  return map[type] || 'file-icon-default'
}

function shortFileId(id) {
  return id ? String(id).slice(0, 8).toUpperCase() : '-'
}

function tableRowClassName({ rowIndex }) {
  if (rowIndex % 2 === 0) return 'even-row'
  return 'odd-row'
}

function getFolderFileCount(folderId) {
  return files.value.filter((file) => (file.folder_id || '') === folderId).length
}

async function fetchFolders() {
  try {
    const data = await getProjectFolders(route.params.id)
    folders.value = Array.isArray(data?.folders) ? data.folders : (Array.isArray(data) ? data : [])
    if (currentFolderId.value && !folders.value.some((folder) => folder.id === currentFolderId.value)) {
      currentFolderId.value = ''
    }
  } catch (err) {
    ElMessage.error(err.message || '加载文件夹失败')
  }
}

function openFolder(folderId = '') {
  currentFolderId.value = folderId || ''
  const query = currentFolderId.value ? { folder_id: currentFolderId.value } : {}
  const navigation = router.replace({ path: route.path, query, hash: route.hash })
  if (navigation?.catch) {
    navigation.catch(() => {})
  }
  if (getFileSearchKeyword()) {
    searchProjectFiles({ silent: true })
  }
}

function isFolderResource(row) {
  return row?.type === 'folder'
}

function isParentResource(row) {
  return row?.type === 'parent'
}

function isFileResource(row) {
  return !row?.type || row.type === 'file'
}

function handleResourceRowClick(row) {
  if (isParentResource(row)) {
    openFolder('')
    return
  }
  if (isFolderResource(row)) {
    openFolder(row.resourceId || row.folder?.id || '')
  }
}

function openCreateFolderDialog() {
  editingFolder.value = null
  folderForm.value = { name: '' }
  folderDialogVisible.value = true
}

function handleFolderAction(command, folder) {
  if (command === 'rename') {
    editingFolder.value = folder
    folderForm.value = { name: folder.name || '' }
    folderDialogVisible.value = true
  } else if (command === 'delete') {
    deleteFolder(folder)
  }
}

async function saveFolder() {
  const name = String(folderForm.value.name || '').trim()
  if (!name) {
    ElMessage.warning('请输入文件夹名称')
    return
  }
  folderSaving.value = true
  try {
    if (editingFolder.value) {
      const updated = await renameProjectFolder(route.params.id, editingFolder.value.id, { name })
      folders.value = folders.value.map((folder) => (folder.id === updated.id ? { ...folder, ...updated } : folder))
      ElMessage.success('文件夹已重命名')
    } else {
      const created = await createProjectFolder(route.params.id, { name })
      folders.value = [...folders.value, created]
      ElMessage.success('文件夹已创建')
    }
    folderDialogVisible.value = false
  } catch (err) {
    ElMessage.error(err.message || '保存文件夹失败')
  } finally {
    folderSaving.value = false
  }
}

async function deleteFolder(folder) {
  try {
    await ElMessageBox.confirm(
      `确定删除文件夹「${folder.name}」吗？仅空文件夹可删除。`,
      '删除文件夹',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await deleteProjectFolder(route.params.id, folder.id)
    folders.value = folders.value.filter((item) => item.id !== folder.id)
    if (currentFolderId.value === folder.id) {
      openFolder('')
    }
    ElMessage.success('文件夹已删除')
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.message || '删除文件夹失败')
    }
  }
}

function openMoveFileDialog(file) {
  movingFile.value = file
  targetFolderId.value = file?.folder_id || ''
  moveFileDialogVisible.value = true
}

async function moveSelectedFile() {
  if (!movingFile.value) return
  moveSaving.value = true
  try {
    const updated = await moveProjectFileToFolder(movingFile.value.id, targetFolderId.value)
    applyFileMetadataPatch(movingFile.value.id, { folder_id: updated.folder_id || '' })
    moveFileDialogVisible.value = false
    ElMessage.success('文件已移动')
  } catch (err) {
    ElMessage.error(err.message || '移动文件失败')
  } finally {
    moveSaving.value = false
  }
}

function closeShareDialog() {
  shareDialogVisible.value = false
  shareDialogLoading.value = false
  shareTarget.value = null
  editingShareToken.value = null
  shareForm.value = buildShareDialogForm()
}

async function openShareDialog(scope = 'project', file = null, options = {}) {
  shareTarget.value = file
  shareDialogLoading.value = true
  shareDialogVisible.value = true
  try {
    const resourceType = scope === 'file' && file ? 'file' : 'project'
    const resourceId = resourceType === 'file' ? file?.id : project.value?.id
    let existingToken = null

    if (resourceId) {
      const data = await listShareTokens()
      shareTokensByResource.value = indexLatestShareTokensByResource(data.items || [])
      existingToken = shareTokensByResource.value[shareResourceKey(resourceType, resourceId)] || null
    }

    editingShareToken.value = existingToken
    shareForm.value = buildShareDialogForm(scope, file, { ...options, existingToken })
  } catch (err) {
    editingShareToken.value = null
    shareForm.value = buildShareDialogForm(scope, file, options)
    ElMessage.error(err.message || '读取现有分享失败，已切换为新建模式')
  } finally {
    shareDialogLoading.value = false
  }
}

async function createShareLink() {
  if (!shareForm.value.resource_id) return
  shareSaving.value = true
  try {
    const currentToken = editingShareToken.value
    const payload = buildShareTokenMutationPayload(shareForm.value, {
      preservePasswordWhenBlank: Boolean(currentToken?.id),
    })

    let data
    let resultTitle
    if (currentToken?.id) {
      const updated = await updateShareToken(currentToken.id, payload)
      data = {
        ...currentToken,
        ...updated,
        token: currentToken.token,
        share_url: updated?.share_url || currentToken.share_url || buildShareHomePath(currentToken.token),
      }
      resultTitle = '分享权限已更新'
    } else {
      data = await createShareToken(payload)
      resultTitle = '分享链接已创建'
    }

    const next = mergeCreatedShareToken({
      project: project.value,
      files: files.value,
      shareTokensByResource: shareTokensByResource.value,
      tokenPayload: data,
    })
    project.value = next.project
    files.value = next.files
    shareTokensByResource.value = next.shareTokensByResource
    editingShareToken.value = data

    const shareTokenValue = data.token || currentToken?.token || ''
    const link = buildShareUrl(shareTokenValue, window.location.origin)
    if (link) {
      await copyToClipboard(link)
      ElMessageBox.alert(link, resultTitle, { confirmButtonText: '确定', type: 'success' })
    } else {
      ElMessage.success(resultTitle)
    }
    closeShareDialog()
  } catch (err) {
    ElMessage.error(err.message || (editingShareToken.value ? '更新分享权限失败' : '创建分享失败'))
  } finally {
    shareSaving.value = false
  }
}

function goToUpload() {
  const query = currentFolderId.value ? { folder_id: currentFolderId.value } : {}
  router.push({ path: `/admin/projects/${route.params.id}/upload`, query })
}

function goToUploadVersion(fileId) {
  router.push({ path: `/admin/projects/${route.params.id}/upload`, query: { fileId } })
}

function goToDiff(fileId) {
  router.push(`/admin/projects/${route.params.id}/diff/${fileId}`)
}
function handleFileRowAction(command, file) {
  if (!file) return
  switch (command) {
    case 'share-access':
      openShareDialog('file', file, { policyMode: 'override_with_token_policy' })
      break
    case 'versions':
      openVersionManage(file)
      break
    case 'diff':
      goToDiff(file.id)
      break
    case 'new-version':
      goToUploadVersion(file.id)
      break
    case 'move':
      openMoveFileDialog(file)
      break
    case 'rebuild-preview':
      rebuildPreview(file)
      break
    case 'delete':
      handleDeleteFile(file)
      break
    default:
      break
  }
}


async function handleDeleteFile(file) {
  try {
    await ElMessageBox.confirm(
      `确定要删除文件「${getFileDisplayName(file)}」吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await deleteFile(file.id)
    files.value = files.value.filter((f) => f.id !== file.id)
    await fetchPreviewStatuses({ silent: true })
    ElMessage.success('文件已删除')
  } catch {
    // 用户取消
  }
}

function buildPreviewCacheKey(version, salt = '') {
  const base = previewFile.value?.id || 'file'
  return `${base}-v${version}-${salt || Date.now()}`
}

function applyLatestPreviewVersion(targetVersion, options = {}) {
  if (!previewFile.value) return
  const nextVersion = Number(targetVersion) || 1
  previewFile.value.current_version = nextVersion
  previewVersion.value = nextVersion
  fileVersions.value = generateVersions(nextVersion)
  previewCacheKey.value = buildPreviewCacheKey(nextVersion, options.cacheKey || 'refresh')
  previewVersionRefreshToken.value = options.refreshToken ? String(options.refreshToken) : ''
  previewUpdateNoticeKey.value = ''
  if (options.reload !== false) {
    loadPreview()
  }
}

async function checkPreviewVersionUpdate(options = {}) {
  if (!previewDialogVisible.value || !previewFile.value?.id) return
  try {
    const data = await client.get(`/files/${previewFile.value.id}/versions`)
    const versions = Array.isArray(data?.versions) ? data.versions : (Array.isArray(data) ? data : [])
    if (!versions.length) return
    const latest = versions.reduce((acc, item) => (Number(item.version) > Number(acc.version) ? item : acc), versions[0])
    const latestVersion = Number(latest.version) || 1
    const currentVersion = Number(previewVersion.value) || 1
    const latestCacheKey = getVersionPreviewCacheKey(latest) || String(latestVersion)
    fileVersions.value = versions
      .map((item) => Number(item.version) || 0)
      .filter(Boolean)
      .sort((a, b) => b - a)
    previewFile.value.current_version = Math.max(Number(previewFile.value.current_version) || 1, latestVersion)
    if (latestVersion > currentVersion && previewUpdateNoticeKey.value !== latestCacheKey) {
      previewUpdateNoticeKey.value = latestCacheKey
      ElMessageBox.confirm(
        `检测到当前文件已有新版本：v${currentVersion} → v${latestVersion}，是否切换到最新版本预览？`,
        '预览版本已更新',
        {
          type: 'info',
          confirmButtonText: '切换到最新版',
          cancelButtonText: '继续查看当前版本',
        }
      ).then(() => {
        applyLatestPreviewVersion(latestVersion, {
          cacheKey: latestCacheKey,
          refreshToken: latest.preview_refresh_token || '',
        })
      }).catch(() => {})
    } else if (hasSameVersionPreviewRefresh(currentVersion, previewVersionRefreshToken.value, latest)) {
      applyLatestPreviewVersion(latestVersion, {
        cacheKey: latestCacheKey,
        refreshToken: latest.preview_refresh_token || '',
        reload: true,
      })
    } else if (options.forceSync && latestVersion >= currentVersion) {
      applyLatestPreviewVersion(latestVersion, {
        cacheKey: latestCacheKey,
        refreshToken: latest.preview_refresh_token || '',
      })
    }
  } catch (error) {
    if (!options.silent) {
      ElMessage.error(error?.message || '检查预览版本失败')
    }
  }
}

function startPreviewVersionPolling() {
  stopPreviewVersionPolling()
  if (!previewDialogVisible.value || !previewFile.value?.id) return
  previewVersionPollTimer.value = window.setInterval(() => {
    checkPreviewVersionUpdate({ silent: true })
  }, 5000)
}

function handlePreview(file) {
  // 清理旧的 blob URL
  if (previewUrl.value && previewUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
  previewFile.value = file
  previewVersion.value = file.current_version || 1
  fileVersions.value = generateVersions(file.current_version || 1)
  previewCacheKey.value = buildPreviewCacheKey(previewVersion.value, 'open')
  previewVersionRefreshToken.value = ''
  previewUpdateNoticeKey.value = ''
  previewDialogVisible.value = true
  loadPreview()
  startPreviewVersionPolling()
}

function generateVersions(currentVersion) {
  const versions = []
  for (let i = currentVersion; i >= 1; i--) {
    versions.push(i)
  }
  return versions
}

async function loadPreview() {
  if (!previewFile.value) return
  previewLoading.value = true
  previewError.value = ''

  // 清理旧的 blob URL / HTML，避免切换版本后继续显示旧内容。
  if (previewUrl.value && previewUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewUrl.value)
  }
  previewUrl.value = ''
  previewHtml.value = ''

  try {
    const url = `/files/${previewFile.value.id}/preview`
    const token = localStorage.getItem('access_token') || ''

    if (previewIsNativeVideo.value || previewIsNativeHtml.value) {
      previewUrl.value = buildAuthenticatedPreviewUrl(
        previewFile.value.id,
        previewVersion.value,
        token,
        previewCacheKey.value,
      )
      return
    }

    // 先通过 axios 拉取一次，复用统一的 Authorization 与错误处理。
    // 若返回 HTML，则写入 srcdoc，避免 iframe 直连时丢失 Bearer token。
    const body = await client.get(url, {
      params: { version: previewVersion.value },
      timeout: 120000,
      responseType: 'text',
      transformResponse: [(data) => data]
    })

    if (typeof body === 'string' && body.trim().startsWith('<')) {
      previewHtml.value = buildPreviewSrcdoc(body, token)
      return
    }

    // PDF 使用带认证信息的 URL，便于浏览器 PDF viewer 分页和缩放。
    previewUrl.value = buildAuthenticatedPreviewUrl(previewFile.value.id, previewVersion.value, token, previewCacheKey.value)
  } catch (err) {
    previewError.value = err.message || '预览加载失败'
    previewUrl.value = ''
    previewHtml.value = ''
  } finally {
    previewLoading.value = false
  }
}

function handlePreviewVersion(version) {
  previewVersion.value = version
  previewCacheKey.value = buildPreviewCacheKey(version, 'manual')
  previewVersionRefreshToken.value = ''
  previewUpdateNoticeKey.value = ''
  loadPreview()
}

async function downloadFile(file) {
  if (!file) return
  try {
    const blob = await client.get(`/files/${file.id}/download`, {
      params: { version: previewVersion.value },
      responseType: 'blob',
      timeout: 120000
    })
    const objectUrl = URL.createObjectURL(blob)
    window.open(objectUrl, '_blank')
    setTimeout(() => URL.revokeObjectURL(objectUrl), 60000)
  } catch (err) {
    ElMessage.error(err.message || '文件下载失败')
  }
}


async function rebuildPreview(file) {
  if (rebuildingIds.value.has(file.id)) return
  rebuildingIds.value = new Set([...rebuildingIds.value, file.id])
  try {
    await enqueuePreviewGeneration([file.id], { force: true })
    await fetchPreviewStatuses({ silent: true })
    ElMessage.success(`${getFileDisplayName(file) || '文件'} 预览重建已入队`)
  } catch (e) {
    ElMessage.error('预览重建失败：' + (e.message || 'unknown'))
  } finally {
    const s = new Set(rebuildingIds.value)
    s.delete(file.id)
    rebuildingIds.value = s
  }
}

async function rebuildAllPreviews() {
  if (rebuildAllLoading.value) return
  const fileIds = getPreviewableFiles().map((file) => file.id)
  if (fileIds.length === 0) {
    ElMessage.info('当前筛选范围内没有可重建预览的 Word/PDF 文件')
    return
  }
  rebuildAllLoading.value = true
  try {
    const resp = await enqueuePreviewGeneration(fileIds, { force: true })
    await fetchPreviewStatuses({ silent: true })
    ElMessage.success(`已提交 ${resp.queued || fileIds.length} 个预览重建任务`)
  } catch (e) {
    ElMessage.error('批量重建失败：' + (e.message || 'unknown'))
  } finally {
    rebuildAllLoading.value = false
  }
}

async function generateMissingPreviews() {
  if (previewGenerateLoading.value) return
  const targetStatuses = new Set(['missing', 'failed', 'interrupted'])
  const fileIds = getPreviewableFiles()
    .filter((file) => targetStatuses.has(getPreviewStatus(file).status))
    .map((file) => file.id)

  if (fileIds.length === 0) {
    ElMessage.info('当前项目没有缺失、失败或中断的预览需要生成')
    return
  }

  previewGenerateLoading.value = true
  try {
    const resp = await enqueuePreviewGeneration(fileIds, { force: false })
    await fetchPreviewStatuses({ silent: true })
    ElMessage.success(`已提交 ${resp.queued || fileIds.length} 个缺失预览生成任务`)
  } catch (e) {
    ElMessage.error('生成缺失预览失败：' + (e.message || 'unknown'))
  } finally {
    previewGenerateLoading.value = false
  }
}

async function cleanupFailedPreviews() {
  if (previewCleanupLoading.value) return
  const targetStatuses = new Set(['failed', 'interrupted'])
  const fileIds = getPreviewableFiles()
    .filter((file) => targetStatuses.has(getPreviewStatus(file).status))
    .map((file) => file.id)

  if (fileIds.length === 0) {
    ElMessage.info('当前项目没有失败或中断的预览缓存需要清理')
    return
  }

  previewCleanupLoading.value = true
  try {
    await Promise.all(fileIds.map((fileId) => clearPreviewCache(fileId)))
    await fetchPreviewStatuses({ silent: true })
    ElMessage.success(`已清理 ${fileIds.length} 个失败/中断预览缓存`)
  } catch (e) {
    ElMessage.error('清理预览缓存失败：' + (e.message || 'unknown'))
  } finally {
    previewCleanupLoading.value = false
  }
}


function onPreviewDialogClosed() {
  // 清理 blob URL 释放内存
  if (previewUrl.value && previewUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewUrl.value)
  }
  stopPreviewVersionPolling()
  previewUrl.value = ''
  previewFile.value = null
  previewLoading.value = false
  previewError.value = ''
  previewCacheKey.value = ''
  previewVersionRefreshToken.value = ''
  previewUpdateNoticeKey.value = ''
}

function getVersionTime(version) {
  // 模拟版本时间
  const baseTime = new Date(previewFile.value?.updated_at || Date.now())
  const diffDays = (previewFile.value?.current_version || 1) - version
  const time = new Date(baseTime.getTime() - diffDays * 24 * 60 * 60 * 1000)
  return formatDate(time.toISOString())
}

function getVersionChangelog(version) {
  return previewFile.value?.changelog || ''
}

const fileEditVisible = ref(false)
const editForm = ref({ display_name: '', description: '', category_id: null, tag_ids: [], cover_image: '' })

function onExpandChange(row, expandedRowsList) {
  if (isFileResource(row) && expandedRowsList.includes(row)) {
    fetchVersionsForRow(row)
  }
}

async function fetchVersionsForRow(row) {
  if (!isFileResource(row)) {
    row._versions = []
    return
  }
  row._loadingVersions = true
  try {
    const data = await client.get(`/files/${row.id}/versions`)
    const items = data.versions || data || []
    row._versions = Array.isArray(items) ? items : []
  } catch {
    row._versions = []
  } finally {
    row._loadingVersions = false
  }
}

// 版本管理
function openVersionManage(file) {
  manageFile.value = file
  versionTimelineVisible.value = true
}

async function fetchRealVersions() {
  if (!manageFile.value) return
  categoryLoading.value = true
  try {
    const data = await client.get(`/files/${manageFile.value.id}/versions`)
    const items = data.versions || data || []
    realVersions.value = Array.isArray(items) ? items : []
  } catch {
    realVersions.value = []
  } finally {
    categoryLoading.value = false
  }
}

async function moveVersionApi(fromIdx, direction) {
  const arr = [...realVersions.value]
  const toIdx = fromIdx + direction
  if (toIdx < 0 || toIdx >= arr.length) return
  ;[arr[fromIdx], arr[toIdx]] = [arr[toIdx], arr[fromIdx]]
  const orderedIds = arr.map(v => v.id)
  try {
    await client.put(`/files/${manageFile.value.id}/versions/reorder`, orderedIds)
    await fetchRealVersions()
    ElMessage.success('排序已更新')
  } catch {
    ElMessage.error('排序失败')
  }
}

async function deleteVersionApi(idx) {
  const v = realVersions.value[idx]
  try {
    await ElMessageBox.confirm(`确定删除 V${v.version}？剩余版本会自动重编号。`, '删除版本', { type: 'warning' })
    await client.delete(`/files/${manageFile.value.id}/versions/${v.id}`)
    await fetchRealVersions()
    ElMessage.success('已删除并重排版本')
  } catch { /* 取消 */ }
}

async function moveVersion(row, v, direction) {
  const arr = [...row._versions]
  const idx = arr.findIndex(x => x.id === v.id)
  if (idx < 0) return
  const toIdx = idx + direction
  if (toIdx < 0 || toIdx >= arr.length) return
  ;[arr[idx], arr[toIdx]] = [arr[toIdx], arr[idx]]
  try {
    await client.put(`/files/${row.id}/versions/reorder`, arr.map(x => x.id))
    row._versions = arr
    ElMessage.success('已调整')
  } catch {
    ElMessage.error('调整失败')
  }
}

async function deleteVersion(row, v) {
  try {
    await ElMessageBox.confirm(`删除 V${v.version}？`, '确认', { type: 'warning' })
    await client.delete(`/files/${row.id}/versions/${v.id}`)
    row._versions = row._versions.filter(x => x.id !== v.id)
    // 重编号本地显示
    row._versions.forEach((vv, i) => { vv.version = i + 1 })
    ElMessage.success('已删除')
  } catch { /* 取消 */ }
}

// 文件设置编辑
async function loadCategories() {
  try {
    const [catRes, tagRes] = await Promise.all([client.get('/categories'), client.get('/tags')])
    categories.value = catRes || []
    tags.value = tagRes || []
  } catch { /* ignore */ }
}

async function ensureAccessGroupsLoaded(force = false) {
  if (accessGroupsLoaded.value && !force) return
  const data = await listAccessGroups()
  accessGroups.value = data.items || []
  accessGroupsLoaded.value = true
}

async function loadFileAccessPolicy(fileId) {
  await ensureAccessGroupsLoaded()
  const policy = await getResourceAccessPolicy('file', fileId)
  fileAccessForm.value = buildResourceAccessFormState({
    scope: 'file',
    defaultVisibility: 'inherit',
    policy,
  })
}

async function loadProjectAccessPolicy() {
  if (!project.value?.id) return
  await ensureAccessGroupsLoaded()
  const policy = await getResourceAccessPolicy('project', project.value.id)
  projectAccessForm.value = buildResourceAccessFormState({
    scope: 'project',
    defaultVisibility: project.value?.is_public ? 'public' : 'private',
    policy,
  })
}

async function loadFileEditData() {
  if (!manageFile.value) return
  await loadCategories()
  try {
    const [data] = await Promise.all([
      client.get(`/files/${manageFile.value.id}`),
      loadFileAccessPolicy(manageFile.value.id),
    ])
    editForm.value = {
      display_name: data.display_name || '',
      description: data.description || '',
      category_id: data.category_id || null,
      tag_ids: (data.tags || []).map(t => t.id || t),
      cover_image: resolveCoverUrl(data.cover_image) || '',
    }
  } catch {
    editForm.value = { display_name: '', description: '', category_id: null, tag_ids: [], cover_image: '' }
  }
}

function openFileEditDialog(file) {
  manageFile.value = file
  fileEditVisible.value = true
}

async function openProjectAccessDialog() {
  projectAccessVisible.value = true
  await loadProjectAccessPolicy()
}

async function saveProjectAccessPolicy() {
  if (!project.value?.id) return
  if (project.value?.is_public && projectAccessForm.value.visibility === 'private') {
    ElMessage.warning('公开项目不能直接设置为禁止公开浏览，请先取消公开状态或改用密码 / 用户组访问。')
    return
  }
  await updateResourceAccessPolicy(
    'project',
    project.value.id,
    buildResourceAccessMutationPayload(projectAccessForm.value, { scope: 'project' }),
  )
  projectAccessVisible.value = false
  ElMessage.success('公开浏览权限已保存')
}

async function saveFileEdit() {
  if (!manageFile.value) return
  try {
    const fid = manageFile.value.id
    const metadataPatch = {
      display_name: editForm.value.display_name,
      description: editForm.value.description,
      category_id: editForm.value.category_id || null,
      cover_image: editForm.value.cover_image || manageFile.value.cover_image || '',
    }
    await client.put(`/cards/${fid}/info`, {
      display_name: metadataPatch.display_name,
      description: metadataPatch.description,
    })
    const versionsData = await client.get(`/files/${fid}/versions`)
    const versionsList = versionsData.versions || versionsData || []
    const latestVersionId = Array.isArray(versionsList) && versionsList.length > 0
      ? versionsList[0].id
      : fid
    await client.put(`/files/${fid}/versions/${latestVersionId}/category-tags`, {
      category_id: metadataPatch.category_id,
      tag_ids: editForm.value.tag_ids || [],
    })
    await updateResourceAccessPolicy(
      'file',
      fid,
      buildResourceAccessMutationPayload(fileAccessForm.value, { scope: 'file' }),
    )
    applyFileMetadataPatch(fid, metadataPatch)
    ElMessage.success('设置已保存')
    fileEditVisible.value = false
    await refreshFileListAfterMetadataChange()
  } catch (err) {
    ElMessage.error('保存失败: ' + (err.message || '未知错误'))
  }
}

async function handleCoverUpload(file) {
  try {
    const form = new FormData()
    form.append('cover', file)
    const data = await client.post(`/cards/${manageFile.value.id}/cover`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    editForm.value.cover_image = resolveCoverUrl(data.cover_image || data.cover_url || data.relative_path)
    ElMessage.success('封面上传成功')
  } catch {
    ElMessage.error('封面上传失败')
  }
  return false // 阻止默认上传
}

function mergeProjectFilesWithExisting(nextFiles = []) {
  const previousById = new Map(files.value.map((item) => [item.id, item]))
  return (nextFiles || []).map((item) => ({
    ...previousById.get(item.id),
    ...normalizeProjectFile(item),
  }))
}

function applyFileMetadataPatch(fileId, patch = {}) {
  const updateFile = (file) => normalizeProjectFile({ ...file, ...patch })
  files.value = files.value.map((file) => (file.id === fileId ? updateFile(file) : file))
  if (manageFile.value?.id === fileId) {
    manageFile.value = updateFile(manageFile.value)
  }
  if (previewFile.value?.id === fileId) {
    previewFile.value = updateFile(previewFile.value)
  }
}

async function refreshFileListAfterMetadataChange() {
  if (getFileSearchKeyword() || activeFileSearchKeyword.value) {
    await searchProjectFiles({ silent: true })
    return
  }
  await fetchProjectData()
}

function getFileDisplayName(file) {
  return file?.display_name || file?.original_filename || file?.filename || ''
}

function getPreviewDialogTitle(file, version) {
  const name = getFileDisplayName(file) || '文档预览'
  const resolvedVersion = Number(version || file?.current_version || 1) || 1
  return `${name} · v${resolvedVersion}`
}

function getSearchableFileName(file) {
  return file?.display_name || file?.original_filename || file?.filename || ''
}

function normalizeProjectFile(file = {}) {
  const originalName = file?.original_filename || file?.filename || file?.display_name || ''
  return {
    ...file,
    original_filename: file?.original_filename || originalName,
    filename: file?.filename || originalName,
    display_name: file?.display_name || '',
    folder_id: file?.folder_id || '',
  }
}

async function syncAfterVersionUploadFromRoute() {
  const refreshFileId = String(route.query.refreshFileId || '')
  if (!refreshFileId) return

  await fetchProjectData()
  await fetchPreviewStatuses({ silent: true })

  const targetFile = files.value.find((item) => item.id === refreshFileId)
  const latestVersion = Number(route.query.latestVersion || 0)
  if (targetFile && latestVersion > 0) {
    targetFile.current_version = latestVersion
  }

  if (previewDialogVisible.value && previewFile.value?.id === refreshFileId && latestVersion > 0) {
    applyLatestPreviewVersion(latestVersion, {
      cacheKey: route.query.previewRefreshToken || latestVersion,
      refreshToken: route.query.previewRefreshToken || '',
      reload: true,
    })
  }

  router.replace({ path: route.path, query: {}, hash: route.hash }).catch(() => {})
}

async function fetchProjectData() {
  loading.value = true
  try {
    const data = await getProject(route.params.id)
    project.value = data
    files.value = mergeProjectFilesWithExisting(data.files || [])
  } catch (err) {
    ElMessage.error('加载项目失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  currentFolderId.value = String(route.query.folder_id || '')
  await fetchProjectData()
  await fetchFolders()
  await fetchPreviewStatuses()
  await syncAfterVersionUploadFromRoute()
})

watch(fileSearchQuery, () => {
  scheduleProjectFileSearch()
})

onUnmounted(() => {
  stopFileSearchDebounce()
  stopPreviewPolling()
  stopPreviewVersionPolling()
})
</script>

<style scoped>
.project-info-card {
  border-radius: 12px;
}

.project-info {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
}

.info-left {
  flex: 1;
}

.project-info h2 {
  font-size: 22px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.project-desc {
  color: #666;
  font-size: 14px;
  margin-bottom: 12px;
  line-height: 1.6;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #999;
  font-size: 13px;
}

.meta-divider {
  color: #ddd;
}

.info-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.info-right :deep(.el-button),
.preview-ops-actions :deep(.el-button),
.action-buttons :deep(.el-button) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  white-space: nowrap;
}

.info-right .btn-hover-lift {
  min-width: 112px;
}

.file-list-card {
  border-radius: 12px;
}

.resource-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  margin-bottom: 12px;
  border: 1px solid #e8eef8;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.06), rgba(14, 165, 233, 0.04));
}

.resource-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.folder-current-name {
  max-width: 260px;
  overflow: hidden;
  color: #334155;
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-list-card :deep(.file-list-card__icon--folder) {
  background: linear-gradient(135deg, rgba(250, 204, 21, 0.2), rgba(245, 158, 11, 0.16));
  color: #b45309;
}

.resource-mobile-shell {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
  padding: 14px;
  border: 1px solid #dbe7f5;
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.95));
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
  position: sticky;
  top: calc(8px + env(safe-area-inset-top));
  z-index: 4;
  backdrop-filter: blur(14px);
}

.resource-mobile-shell__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.resource-mobile-shell__eyebrow {
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #2563eb;
}

.resource-mobile-shell__title {
  margin: 4px 0 0;
  color: #172033;
  font-size: 18px;
  font-weight: 700;
}

.resource-mobile-shell__details {
  border-top: 1px solid #e2e8f0;
  padding-top: 10px;
}

.resource-mobile-shell__details summary {
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.resource-mobile-shell__details p {
  margin: 10px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.move-file-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 14px;
  border-radius: 12px;
  background: #f8fafc;
  color: #334155;
  font-weight: 600;
}

.move-folder-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preview-ops-card {
  border-radius: 14px;
  background:
    linear-gradient(135deg, rgba(15, 23, 42, 0.03), rgba(37, 99, 235, 0.04)),
    #fff;
  border: 1px solid #e5edf7;
}

.preview-ops-card :deep(.el-card__header) {
  border-bottom-color: #e8eef7;
  padding: 14px 18px;
}

.preview-ops-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.preview-ops-title {
  display: block;
  color: #172033;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.preview-ops-subtitle {
  display: block;
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  font-weight: 400;
}

.preview-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.preview-summary-item {
  position: relative;
  overflow: hidden;
  min-height: 86px;
  padding: 14px 16px;
  border: 1px solid #edf2f7;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
}

.preview-summary-item::after {
  position: absolute;
  right: -22px;
  bottom: -28px;
  width: 72px;
  height: 72px;
  content: '';
  border-radius: 999px;
  opacity: 0.16;
}

.preview-summary-ready::after { background: #22c55e; }
.preview-summary-active::after { background: #f59e0b; }
.preview-summary-problem::after { background: #ef4444; }
.preview-summary-storage::after { background: #3b82f6; }

.summary-label {
  display: block;
  color: #6b7280;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.preview-summary-item strong {
  display: block;
  margin-top: 8px;
  color: #111827;
  font-size: 24px;
  line-height: 1.1;
}

.preview-summary-item small {
  display: block;
  margin-top: 6px;
  color: #7c8798;
  font-size: 12px;
}

.preview-diagnostics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.preview-diagnostic-card {
  min-height: 78px;
  padding: 12px 14px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.92), rgba(255, 255, 255, 0.9));
}

.preview-diagnostic-card strong {
  display: block;
  margin-top: 7px;
  color: #1f2937;
  font-size: 14px;
  line-height: 1.3;
}

.preview-diagnostic-card small {
  display: block;
  margin-top: 6px;
  overflow: hidden;
  color: #64748b;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-stat-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.preview-largest-list {
  display: grid;
  gap: 2px;
  margin-top: 2px;
}

.preview-storage-breakdown,
.preview-largest-files,
.preview-file-type-stats,
.preview-queue-state {
  min-width: 0;
}

.preview-ops-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}

.preview-polling-hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #b45309;
  font-size: 12px;
}

.preview-polling-hint::before {
  width: 7px;
  height: 7px;
  content: '';
  border-radius: 999px;
  background: #f59e0b;
  box-shadow: 0 0 0 5px rgba(245, 158, 11, 0.14);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.file-list-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.file-table-scroll {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
}

.file-search-input {
  width: 260px;
}
.file-type-filter { width: 110px; }
.file-tag-filter { width: 180px; }
.file-cat-filter { width: 130px; }
.file-preview-filter { width: 140px; }
.tag-dot { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 4px; vertical-align: middle; }

.file-search-hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 24px;
  padding: 0 10px;
  border: 1px solid rgba(59, 130, 246, 0.18);
  border-radius: 999px;
  background: rgba(239, 246, 255, 0.72);
  color: #2563eb;
  font-size: 12px;
  line-height: 1;
}

.file-search-hint.is-loading :deep(.el-icon) {
  animation: previewSpin 0.9s linear infinite;
}

.file-table {
  cursor: pointer;
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

.file-table :deep(.el-table__row) {
  transition: background-color 0.15s ease;
}

.file-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

.file-table :deep(.even-row) {
  background-color: #fafafa;
}

.file-table :deep(.odd-row) {
  background-color: #ffffff;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-name-cell--folder {
  cursor: pointer;
}

.file-icon-pdf { color: #E74C3C; }
.file-icon-docx { color: #2980b9; }
.file-icon-xlsx { color: #27AE60; }
.file-icon-default { color: #909399; }
.file-icon-folder { color: #d97706; }

.file-info {
  display: flex;
  flex-direction: column;
}

.file-name {
  font-weight: 500;
  color: #333;
}

.file-path {
  font-size: 12px;
  color: #999;
}

.file-size, .file-time {
  font-size: 13px;
  color: #666;
}

.file-meta-cell {
  display: grid;
  gap: 4px;
  min-width: 0;
  color: #64748b;
  font-size: 12px;
}

.file-meta-main {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  white-space: nowrap;
}

.file-meta-sub {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #9aa4b2;
}

.preview-status-cell {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.preview-status-line {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.preview-status-active {
  animation: previewPulse 1.8s ease-in-out infinite;
}

.preview-error-icon {
  color: #f56c6c;
  cursor: help;
}

.preview-storage-text {
  color: #8a95a7;
  font-size: 12px;
}

.preview-detail-text,
.preview-updated-text {
  color: #64748b;
  font-size: 11px;
  line-height: 1.35;
}

.preview-updated-text {
  color: #9aa4b2;
}

.resource-cell-placeholder {
  color: #c0c4cc;
}

.preview-detail-compact {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-buttons {
  display: inline-flex;
  gap: 6px;
  justify-content: center;
  flex-wrap: wrap;
  align-items: center;
}

.action-buttons .btn-label {
  display: inline-block;
  min-width: 2em;
}

.action-buttons-compact {
  gap: 2px;
  flex-wrap: nowrap;
  width: 100%;
  white-space: nowrap;
}

.action-buttons-compact :deep(.el-button) {
  margin-left: 0;
  padding-inline: 5px;
}

.more-action-button {
  color: #606266;
}

.more-action-button:hover {
  color: var(--workspace-blue, #2f5d8c);
}

/* 版本展开行 */
.version-expand { padding: 12px 20px; background: #f8fafc; border-top: 1px solid #e5e7eb; }
.version-expand--empty { color: #94a3b8; }
.version-expand-header { margin-bottom: 10px; }
.ve-title { font-weight: 600; font-size: 13px; color: #374151; }
.version-list { display: flex; flex-direction: column; gap: 4px; }
.version-row { display: flex; align-items: center; gap: 12px; padding: 6px 12px; background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 12px; }
.version-row-latest { border-left: 3px solid #22c55e; }
.vr-num { font-weight: 700; color: #6366f1; min-width: 32px; }
.vr-hash { color: #9ca3af; font-family: monospace; font-size: 11px; min-width: 70px; }
.vr-size { color: #6b7280; min-width: 60px; }
.vr-time { color: #9ca3af; flex: 1; }
.vr-actions { display: flex; gap: 2px; }

/* 版本管理对话框 */
.version-manage { min-height: 200px; }
.vm-list { display: flex; flex-direction: column; gap: 6px; }
.vm-row { display: flex; align-items: center; gap: 12px; padding: 8px 14px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; }
.vm-latest { border-left: 3px solid #22c55e; background: #f0fdf4; }
.vm-num { min-width: 44px; }
.vm-meta { color: #6b7280; font-size: 12px; flex: 1; }
.vm-time { color: #9ca3af; font-size: 12px; }
.vm-actions { display: flex; gap: 4px; }

/* 分类标签 */
.cat-tag-form { display: flex; flex-direction: column; gap: 16px; }
.ct-item { display: flex; flex-direction: column; gap: 4px; }
.ct-label { font-size: 13px; font-weight: 600; color: #374151; }

/* 文件设置 */
.file-edit-form .el-form-item { margin-bottom: 14px; }
.cover-preview { display: flex; align-items: center; gap: 12px; }
.share-token-form { display: flex; flex-direction: column; gap: 10px; }
.share-access-section {
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(255, 255, 255, 0.98));
}
.share-access-section__title {
  margin-bottom: 12px;
  color: #172033;
  font-size: 14px;
  font-weight: 700;
}
.share-access-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.share-limit-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.share-limit-grid :deep(.el-input-number) { width: 100%; }
.share-field-note {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}
.share-dialog-hint { color: #64748b; font-size: 12px; line-height: 1.6; }

/* 预览对话框 */
:global(.preview-dialog-mask) {
  z-index: 3000 !important;
}

:global(.preview-dialog) {
  z-index: 3001 !important;
  max-width: calc(100vw - 64px);
}

:global(.preview-dialog .el-dialog__body) {
  padding: 16px !important;
}

.preview-container {
  --admin-preview-scale: 0.82;
  height: 70vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fb;
}

.preview-loading, .preview-error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #666;
}

.preview-error {
  color: #E74C3C;
}

.preview-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.preview-body {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
  padding: 0 8px 12px;
}

.preview-iframe-container {
  width: min(100%, 1040px);
  height: 100%;
  min-height: 500px;
  margin: 0 auto;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 8px;
  background: #fff;
  zoom: var(--admin-preview-scale);
  transform-origin: top center;
}

.preview-iframe--native-html {
  zoom: 1;
}

.preview-video-container {
  width: 100%;
  height: 100%;
  min-height: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  background: #0f172a;
  border-radius: 12px;
  overflow: hidden;
}

.preview-video-player {
  width: 100%;
  height: min(70vh, 720px);
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  background: #000;
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
  color: #999;
}

.preview-placeholder p {
  margin: 0;
  font-size: 16px;
}

/* 版本时间线 */
.version-timeline {
  padding: 8px 0;
}

.version-card {
  padding: 12px;
}

.version-card h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.version-card p {
  margin: 0 0 12px;
  font-size: 13px;
  color: #666;
}

.text-muted {
  color: #999 !important;
  font-style: italic;
}

.version-actions {
  display: flex;
  gap: 8px;
}

@media (max-width: 900px) {
  .file-table-scroll {
    overflow-x: auto;
  }

  .file-table {
    min-width: 760px;
  }
}

/* 响应式适配 */
@media (max-width: 768px) {
  .resource-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .resource-breadcrumb {
    width: 100%;
    overflow: visible;
    flex-wrap: wrap;
    row-gap: 8px;
    white-space: normal;
  }

  .folder-current-name {
    flex: 1 1 100%;
    max-width: 100%;
    white-space: normal;
    word-break: break-word;
  }

  .project-info {
    flex-direction: column;
  }

  .info-right {
    width: 100%;
    align-items: stretch;
  }

  .file-list-toolbar {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .preview-ops-header {
    align-items: stretch;
    flex-direction: column;
  }

  .preview-summary-grid,
  .preview-diagnostics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .file-search-input,
  .file-tag-filter {
    grid-column: 1 / -1;
  }

  .share-access-grid,
  .share-limit-grid {
    grid-template-columns: 1fr;
  }

  .file-search-hint {
    grid-column: 1 / -1;
    justify-content: center;
  }

  .file-search-input,
  .file-type-filter,
  .file-tag-filter,
  .file-cat-filter,
  .file-preview-filter {
    width: 100%;
  }

  .action-buttons {
    flex-wrap: wrap;
  }

  .version-expand {
    padding: 10px;
  }

  .version-row,
  .vm-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }

  .vr-actions,
  .vm-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .preview-container {
    height: calc(100dvh - 168px);
    min-height: 420px;
  }

  .preview-header {
    align-items: stretch;
    flex-direction: column;
    gap: 8px;
  }

  .preview-iframe-container {
    min-height: 360px;
  }

  .preview-video-container {
    min-height: 360px;
    padding: 8px;
  }

  .preview-video-player {
    height: min(52vh, 420px);
  }
}

@keyframes previewFadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes previewPulse {
  0%, 100% { filter: saturate(1); transform: translateY(0); }
  50% { filter: saturate(1.25); transform: translateY(-1px); }
}

@keyframes previewSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
