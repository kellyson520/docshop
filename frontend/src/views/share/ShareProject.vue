<template>
  <div class="share-project motion-page motion-page--share">
    <template v-if="loading && !error">
      <el-card shadow="never" class="project-info-card">
        <el-skeleton :rows="2" animated />
      </el-card>
      <el-card shadow="never" class="file-list-card">
        <el-skeleton :rows="6" animated />
      </el-card>
    </template>

    <el-card
      v-if="project"
      shadow="never"
      class="project-info-card"
      :class="{ 'project-info-card--mobile-shell': isMobile }"
    >
      <template v-if="isMobile">
        <div class="share-project-mobile-shell" data-testid="share-project-mobile-shell">
          <div class="share-project-mobile-shell__hero">
            <span class="share-project-mobile-shell__eyebrow">共享项目</span>
            <h2 class="project-title project-title--mobile">{{ project.name }}</h2>
            <div class="share-project-mobile-stats">
              <span class="share-project-mobile-stat">{{ totalFileCount }} 个文件</span>
              <span class="share-project-mobile-stat">{{ totalFolderCount }} 个文件夹</span>
            </div>
          </div>

          <details class="share-project-mobile-details">
            <summary data-testid="share-project-mobile-info-summary">项目信息</summary>
            <p class="project-desc">{{ project.description || '暂无描述' }}</p>
          </details>
        </div>
      </template>
      <template v-else>
        <h2 class="project-title">{{ project.name }}</h2>
        <p class="project-desc">{{ project.description || '暂无描述' }}</p>
      </template>
    </el-card>

    <el-card
      v-if="project"
      shadow="never"
      class="file-list-card"
      :class="{ 'file-list-card--mobile-shell': isMobile }"
    >
      <template v-if="!isMobile" #header>
        <div class="card-header">
          <span class="card-title">文件列表</span>
          <el-tag type="info" effect="plain">显示 {{ filteredFiles.length }} / {{ files.length }} 个文件</el-tag>
        </div>
      </template>

      <div
        v-if="isMobile"
        class="share-project-mobile-resource-head"
        data-testid="share-project-mobile-resource-head"
      >
        <div>
          <span class="share-project-mobile-resource-head__eyebrow">资源列表</span>
          <div class="share-project-mobile-resource-head__title">
            {{ currentFolder?.name || '全部资源' }}
          </div>
        </div>
        <el-tag type="info" effect="plain">{{ resourceItems.length }} 个资源</el-tag>
      </div>

      <div class="file-search-bar">
        <el-input
          v-model="fileKeyword"
          data-testid="share-file-search"
          placeholder="搜索项目内文件名、类型或最新变更…"
          :prefix-icon="Search"
          clearable
          class="share-file-search"
        />
      </div>

      <div v-if="folders.length" class="resource-toolbar">
        <div class="resource-breadcrumb">
          <button
            type="button"
            class="folder-root-btn"
            :class="{ 'folder-root-btn--active': currentFolderId === null }"
            data-folder-id="all-files"
            @click="openFolder(null)"
          >
            <el-icon><FolderOpened /></el-icon>
            全部文件
          </button>
          <button
            type="button"
            class="folder-root-btn"
            :class="{ 'folder-root-btn--active': currentFolderId === '' }"
            data-folder-id="root"
            @click="openFolder('')"
          >
            <el-icon><Folder /></el-icon>
            根目录
          </button>
          <span v-if="currentFolder" class="folder-current-name">/ {{ currentFolder.name }}</span>
          <el-tag size="small" type="info" effect="plain">{{ resourceItems.length }} 个资源</el-tag>
        </div>
      </div>

      <el-table
        v-if="!isMobile"
        :data="resourceItems"
        stripe
        class="file-table"
        @row-click="handleResourceRowClick"
      >
        <el-table-column label="名称" min-width="300">
          <template #default="{ row }">
            <div class="resource-name-cell" :class="{ 'resource-name-cell--folder': row.type !== 'file' }">
              <el-icon :size="18" class="resource-icon">
                <FolderOpened v-if="row.type === 'parent'" />
                <Folder v-else-if="row.type === 'folder'" />
                <component v-else :is="getFileTypeIcon(row.file_type)" />
              </el-icon>
              <div class="resource-copy">
                <span v-if="row.type === 'folder'" :data-testid="`resource-folder-item-${row.resourceId}`">{{ row.name }}</span>
                <span v-else-if="row.type === 'parent'">{{ row.name }}</span>
                <span v-else>{{ getShareFileDisplayName(row) }}</span>

                <small v-if="row.type === 'folder'">单击打开文件夹</small>
                <small v-else-if="row.type === 'parent'">返回根目录</small>
                <small v-else>{{ row.latest_changelog || '暂无最新变更' }}</small>

                <small v-if="row.type === 'folder' && row.folderPreviewText">{{ row.folderPreviewText }}</small>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.type === 'folder'" size="small" type="warning" effect="plain">文件夹</el-tag>
            <el-tag v-else-if="row.type === 'parent'" size="small" effect="plain">返回</el-tag>
            <el-tag v-else size="small" :type="getFileTypeTagType(row.file_type)" effect="light">
              {{ row.file_type?.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="信息" width="220">
          <template #default="{ row }">
            <div class="resource-meta-cell">
              <template v-if="row.type === 'folder'">
                <span>{{ row.fileCount }} 个文件</span>
                <small>{{ row.folderPreviewText || '支持整文件夹打包下载' }}</small>
              </template>
              <template v-else-if="row.type === 'parent'">
                <span>返回上一级</span>
                <small>回到根目录</small>
              </template>
              <template v-else>
                <span>v{{ row.current_version || 1 }}</span>
                <small>{{ formatDate(row.updated_at) }}</small>
              </template>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="340" align="left">
          <template #default="{ row }">
            <div v-if="row.type === 'folder'" class="action-buttons">
              <el-button text type="primary" size="small" @click.stop="openFolder(row.resourceId)">
                <el-icon><FolderOpened /></el-icon> 打开
              </el-button>
              <el-button
                v-if="allowDownload"
                text
                type="success"
                size="small"
                @click.stop="downloadFolderBundle(row.folder)"
              >
                <el-icon><Download /></el-icon> 打包下载
              </el-button>
              <el-tooltip v-else :content="CLOSED_DOWNLOAD_COPY" placement="top">
                <el-button text :disabled="true" size="small">
                  <el-icon><Download /></el-icon> {{ CLOSED_DOWNLOAD_BUTTON_COPY }}
                </el-button>
              </el-tooltip>
            </div>
            <div v-else-if="row.type === 'parent'" class="action-buttons">
              <el-button text type="primary" size="small" @click.stop="openFolder('')">
                <el-icon><FolderOpened /></el-icon> 返回
              </el-button>
            </div>
            <div v-else class="action-buttons">
              <template v-if="allowPreview">
                <el-button text type="info" size="small" @click.stop="previewFile(row)" class="action-btn">
                  <el-icon><View /></el-icon> 预览
                </el-button>
              </template>
              <el-tooltip v-else :content="CLOSED_PREVIEW_COPY" placement="top">
                <el-button text :disabled="true" size="small" class="action-btn">
                  <el-icon><View /></el-icon> 预览
                </el-button>
              </el-tooltip>
              <template v-if="allowVersions">
                <el-button text type="primary" size="small" @click.stop="goToFile(row.id)" class="action-btn">
                  <el-icon><Clock /></el-icon> 版本
                </el-button>
              </template>
              <el-tooltip v-else :content="CLOSED_VERSIONS_COPY" placement="top">
                <el-button text :disabled="true" size="small" class="action-btn">
                  <el-icon><Clock /></el-icon> 版本
                </el-button>
              </el-tooltip>
              <template v-if="allowDiff">
                <el-button text type="warning" size="small" @click.stop="goToDiff(row.id)" class="action-btn">
                  <el-icon><Sort /></el-icon> 变更
                </el-button>
              </template>
              <el-tooltip v-else :content="CLOSED_DIFF_COPY" placement="top">
                <el-button text :disabled="true" size="small" class="action-btn">
                  <el-icon><Sort /></el-icon> 变更
                </el-button>
              </el-tooltip>
              <template v-if="allowDownload">
                <el-button
                  v-if="hasSingleDownloadFormat(row)"
                  text
                  type="success"
                  size="small"
                  data-testid="share-project-download-original"
                  @click.stop="handleDownloadLatest(row)"
                  class="action-btn"
                >
                  <el-icon><Download /></el-icon> 下载
                </el-button>
                <el-dropdown
                  v-else-if="hasMultipleDownloadFormats(row)"
                  trigger="click"
                  @command="(fmt) => handleDownloadLatest(row, fmt)"
                >
                  <el-button text type="success" size="small" class="action-btn" aria-label="选择下载格式">
                    <el-icon><Download /></el-icon> 下载
                    <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item
                        v-for="format in getDownloadFormats(row)"
                        :key="format"
                        :command="format"
                      >
                        <el-icon><Document /></el-icon> {{ getDownloadFormatLabel(format) }}
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
              <el-tooltip v-else :content="CLOSED_DOWNLOAD_COPY" placement="top">
                <el-button text :disabled="true" size="small" class="action-btn">
                  <el-icon><Download /></el-icon> {{ CLOSED_DOWNLOAD_BUTTON_COPY }}
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <FileListCards
        v-else
        :items="resourceItems"
        variant="share"
        test-id="share-mobile-file-list"
      >
        <template #icon="{ item }">
          <div class="file-list-card__icon file-list-card__icon--share" :class="{ 'file-list-card__icon--folder': item.type !== 'file' }">
            <el-icon :size="18">
              <FolderOpened v-if="item.type === 'parent'" />
              <Folder v-else-if="item.type === 'folder'" />
              <component v-else :is="getFileTypeIcon(item.file_type)" />
            </el-icon>
          </div>
        </template>

        <template #title="{ item }">
          <span v-if="item.type === 'folder'" :data-testid="`resource-folder-item-${item.resourceId}`">{{ item.name }}</span>
          <span v-else-if="item.type === 'parent'">返回上一级</span>
          <span v-else>{{ getShareFileDisplayName(item) }}</span>
        </template>

        <template #subtitle="{ item }">
          <template v-if="item.type === 'folder'">文件夹 · {{ item.fileCount }} 个文件</template>
          <template v-else-if="item.type === 'parent'">回到根目录</template>
          <template v-else>{{ item.file_type?.toUpperCase() || 'FILE' }} · v{{ item.current_version || 1 }}</template>
        </template>

        <template #badges="{ item }">
          <el-tag v-if="item.type === 'folder'" size="small" type="warning" effect="plain">文件夹</el-tag>
          <template v-else>
            <el-tag size="small" :type="getFileTypeTagType(item.file_type)" effect="light">
              {{ item.file_type?.toUpperCase() }}
            </el-tag>
            <el-tag size="small" type="info" effect="plain">v{{ item.current_version || 1 }}</el-tag>
          </template>
        </template>

        <template #meta="{ item }">
          <span v-if="item.type === 'folder'">单击打开文件夹</span>
          <span v-else-if="item.type === 'parent'">点击返回根目录</span>
          <span v-else>{{ formatDate(item.updated_at) }}</span>
        </template>

        <template #summary="{ item }">
          <span v-if="item.type === 'folder'" class="mobile-changelog">{{ item.folderPreviewText || '支持整文件夹打包下载' }}</span>
          <span v-else class="mobile-changelog">{{ item.latest_changelog || '暂无最新变更' }}</span>
        </template>

        <template #actions="{ item }">
          <template v-if="item.type === 'folder'">
            <el-button text type="primary" size="small" @click.stop="openFolder(item.resourceId)" class="action-btn">
              <el-icon><FolderOpened /></el-icon> 打开
            </el-button>
            <el-button
              v-if="allowDownload"
              text
              type="success"
              size="small"
              @click.stop="downloadFolderBundle(item.folder)"
              class="action-btn"
            >
              <el-icon><Download /></el-icon> 打包下载
            </el-button>
            <el-tooltip v-else :content="CLOSED_DOWNLOAD_COPY" placement="top">
              <el-button text :disabled="true" size="small" class="action-btn">
                <el-icon><Download /></el-icon> {{ CLOSED_DOWNLOAD_BUTTON_COPY }}
              </el-button>
            </el-tooltip>
          </template>
          <template v-else-if="item.type === 'parent'">
            <el-button text type="primary" size="small" @click.stop="openFolder('')" class="action-btn">
              <el-icon><FolderOpened /></el-icon> 返回
            </el-button>
          </template>
          <template v-else>
            <template v-if="allowPreview">
              <el-button text type="info" size="small" @click.stop="previewFile(item)" class="action-btn">
                <el-icon><View /></el-icon> 预览
              </el-button>
            </template>
            <el-tooltip v-else :content="CLOSED_PREVIEW_COPY" placement="top">
              <el-button text :disabled="true" size="small" class="action-btn">
                <el-icon><View /></el-icon> 预览
              </el-button>
            </el-tooltip>
            <template v-if="allowVersions">
              <el-button text type="primary" size="small" @click.stop="goToFile(item.id)" class="action-btn">
                <el-icon><Clock /></el-icon> 版本
              </el-button>
            </template>
            <el-tooltip v-else :content="CLOSED_VERSIONS_COPY" placement="top">
              <el-button text :disabled="true" size="small" class="action-btn">
                <el-icon><Clock /></el-icon> 版本
              </el-button>
            </el-tooltip>
            <template v-if="allowDiff">
              <el-button text type="warning" size="small" @click.stop="goToDiff(item.id)" class="action-btn">
                <el-icon><Sort /></el-icon> 变更
              </el-button>
            </template>
            <el-tooltip v-else :content="CLOSED_DIFF_COPY" placement="top">
              <el-button text :disabled="true" size="small" class="action-btn">
                <el-icon><Sort /></el-icon> 变更
              </el-button>
            </el-tooltip>
            <template v-if="allowDownload">
              <el-button
                v-if="hasSingleDownloadFormat(item)"
                text
                type="success"
                size="small"
                data-testid="share-project-download-original"
                @click.stop="handleDownloadLatest(item)"
                class="action-btn"
              >
                <el-icon><Download /></el-icon> 下载
              </el-button>
              <el-dropdown
                v-else-if="hasMultipleDownloadFormats(item)"
                trigger="click"
                @command="(fmt) => handleDownloadLatest(item, fmt)"
              >
                <el-button text type="success" size="small" class="action-btn" aria-label="选择下载格式">
                  <el-icon><Download /></el-icon> 下载
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      v-for="format in getDownloadFormats(item)"
                      :key="format"
                      :command="format"
                    >
                      {{ getDownloadFormatLabel(format) }}
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
            <el-tooltip v-else :content="CLOSED_DOWNLOAD_COPY" placement="top">
              <el-button text :disabled="true" size="small" class="action-btn">
                <el-icon><Download /></el-icon> {{ CLOSED_DOWNLOAD_BUTTON_COPY }}
              </el-button>
            </el-tooltip>
          </template>
        </template>
      </FileListCards>

      <el-empty
        v-if="!loading && files.length === 0"
        description="暂无文件"
      />
      <el-empty
        v-else-if="!loading && resourceItems.length === 0"
        description="没有匹配的资源，请换个关键词"
      />
    </el-card>

    <div v-if="unlockRequired" data-testid="share-unlock-card">
      <el-card shadow="never" class="unlock-card">
        <template #header>
          <span class="card-title">输入分享密码</span>
        </template>

        <div class="unlock-form">
          <p class="unlock-copy">该分享已启用访问密码，请先解锁后再查看。</p>
          <el-input
            v-model="unlockPassword"
            type="password"
            show-password
            clearable
            placeholder="请输入分享密码"
            data-testid="share-unlock-password"
          />
          <p v-if="unlockError" class="unlock-error">{{ unlockError }}</p>
          <div class="unlock-actions">
            <el-button
              type="primary"
              :loading="unlocking"
              data-testid="share-unlock-submit"
              @click="submitUnlock"
            >
              解锁访问
            </el-button>
            <el-button :disabled="unlocking" @click="goHome">返回首页</el-button>
          </div>
        </div>
      </el-card>
    </div>

    <el-card v-if="error" shadow="never" class="error-card">
      <el-result icon="error" title="访问失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="goHome">返回首页</el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  Clock,
  Document,
  Download,
  Folder,
  FolderOpened,
  Search,
  Sort,
  View,
} from '@element-plus/icons-vue'
import { getShareProject } from '@/api/share'
import FileListCards from '@/components/file/FileListCards.vue'
import { useResponsive } from '@/composables/useResponsive'
import { useShareSession } from '@/composables/useShareSession'
import { usePublicAccessSession } from '@/composables/usePublicAccessSession'
import { formatDate, getFileTypeIcon, downloadViaIframe } from '@/utils'
import {
  getDownloadFormatLabel,
  hasMultipleDownloadFormats as resolveHasMultipleDownloadFormats,
  hasSingleDownloadFormat as resolveHasSingleDownloadFormat,
  isOriginalDownloadFormat as resolveIsOriginalDownloadFormat,
  resolveDownloadFormats,
} from '@/utils/downloadFormats'
import { filterShareFiles } from '@/utils/shareProjectSearch'
import { getShareResourceUrl } from '@/utils/shareResourceTickets'
import {
  buildShareDiffPath,
  buildShareFilePath,
  buildSharePreviewPath,
} from '@/utils/shareRoute'

const DEFAULT_SHARE_PERMISSIONS = {
  allow_download: true,
  allow_preview: true,
  allow_diff: true,
  allow_versions: true,
}
const CLOSED_DOWNLOAD_COPY = '当前分享未开放下载'
const CLOSED_DOWNLOAD_BUTTON_COPY = '禁止下载'
const CLOSED_PREVIEW_COPY = '当前分享未开放预览'
const CLOSED_VERSIONS_COPY = '当前分享未开放版本历史'
const CLOSED_DIFF_COPY = '当前分享未开放变更'

const route = useRoute()
const router = useRouter()

const token = route.params.token
const shareSession = useShareSession(token)
const publicAccessSession = usePublicAccessSession(token, 'project', '')
const project = ref(null)
const files = ref([])
const folders = ref([])
const loading = ref(false)
const error = ref('')
const fileKeyword = ref('')
const shareInfo = ref({ ...DEFAULT_SHARE_PERMISSIONS })
const currentFolderId = ref('')
const unlockRequired = ref(false)
const unlockMode = ref('share')
const unlockPassword = ref('')
const unlocking = ref(false)
const unlockError = ref('')
const { isMobile } = useResponsive()
let publicAccessHeartbeatTimer = null

const allowDownload = computed(() => shareInfo.value?.allow_download !== false)
const allowPreview = computed(() => shareInfo.value?.allow_preview !== false)
const allowDiff = computed(() => shareInfo.value?.allow_diff !== false)
const allowVersions = computed(() => shareInfo.value?.allow_versions !== false)
const totalFileCount = computed(() => files.value.length)
const totalFolderCount = computed(() => folders.value.length)
const currentFolder = computed(() => (
  folders.value.find((folder) => folder.id === currentFolderId.value) || null
))
const filesInCurrentFolder = computed(() => {
  if (currentFolderId.value === null) return files.value
  return files.value.filter((file) => (file?.folder_id || '') === String(currentFolderId.value || ''))
})
const filteredFiles = computed(() => filterShareFiles(filesInCurrentFolder.value, fileKeyword.value))
const visibleFolders = computed(() => {
  if (String(fileKeyword.value || '').trim()) return []
  if (currentFolderId.value !== '') return []
  return folders.value
})
const parentResourceItem = computed(() => {
  if (currentFolderId.value == null || currentFolderId.value === '') return null
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
      folderPreviewText: getFolderPreviewText(folder.id),
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

function getShareFileDisplayName(file) {
  return file?.display_name || file?.original_filename || file?.filename || ''
}

function isSharePasswordRequiredError(err) {
  return shareSession.isPasswordRequiredError(err)
}

function isResourcePasswordRequiredError(err) {
  return publicAccessSession.isResourcePasswordRequiredError(err)
}

function getUnlockErrorMessage(err) {
  return unlockMode.value === 'resource'
    ? publicAccessSession.getUnlockErrorMessage(err)
    : shareSession.getUnlockErrorMessage(err)
}

function buildAccessHeaders() {
  return shareSession.withShareHeaders(publicAccessSession.withAccessHeaders())
}

function getFileTypeTagType(type) {
  const map = { pdf: 'danger', docx: 'primary', doc: 'primary', xlsx: 'success', xls: 'success' }
  return map[type] || 'info'
}

function openFolder(folderId) {
  currentFolderId.value = folderId == null ? null : String(folderId || '')
}

function getFolderFiles(folderId) {
  return files.value.filter((file) => (file?.folder_id || '') === String(folderId || ''))
}

function getFolderFileCount(folderId) {
  return getFolderFiles(folderId).length
}

function getFolderPreviewText(folderId) {
  const names = getFolderFiles(folderId)
    .map((file) => getShareFileDisplayName(file))
    .filter(Boolean)
    .slice(0, 3)

  if (!names.length) return ''
  return `包含：${names.join('、')}`
}

function handleResourceRowClick(row) {
  if (row?.type === 'parent') {
    openFolder('')
    return
  }
  if (row?.type === 'folder') {
    openFolder(row.resourceId || row.folder?.id || '')
  }
}

function getLatestVersionEntry(file) {
  const versions = Array.isArray(file?.versions) ? file.versions.filter(Boolean) : []
  if (versions.length === 0) return null

  const currentVersionNumber = Number(file?.current_version || 0)
  const exactCurrent = versions.find((version) => Number(version?.version || 0) === currentVersionNumber && version?.id)
  if (exactCurrent) return exactCurrent

  return [...versions].sort((left, right) => {
    const leftVersion = Number(left?.version || 0)
    const rightVersion = Number(right?.version || 0)
    return rightVersion - leftVersion
  })[0] || versions[0]
}

function getDownloadFormats(file) {
  return resolveDownloadFormats(file, getLatestVersionEntry(file))
}

function hasSingleDownloadFormat(file) {
  return file?.type === 'file' && resolveHasSingleDownloadFormat(file, getLatestVersionEntry(file))
}

function hasMultipleDownloadFormats(file) {
  return file?.type === 'file' && resolveHasMultipleDownloadFormats(file, getLatestVersionEntry(file))
}

function goToFile(fileId) {
  const path = buildShareFilePath(token, fileId)
  if (path) {
    router.push(path)
  }
}

function goToDiff(fileId) {
  const path = buildShareDiffPath(token, fileId)
  if (path) {
    router.push(path)
  }
}

function previewFile(file) {
  const path = buildSharePreviewPath(token, file?.id)
  if (!path) return
  router.push(path)
}

async function downloadFolderBundle(folder) {
  if (!folder?.id) return
  if (!allowDownload.value) {
    ElMessage.warning(CLOSED_DOWNLOAD_COPY)
    return
  }
  const url = await getShareResourceUrl({
    token,
    session: shareSession,
    accessSession: publicAccessSession,
    kind: 'folder_download',
    folderId: folder.id,
  })
  downloadViaIframe(url)
}

async function handleDownloadLatest(file, format) {
  const latestVersion = getLatestVersionEntry(file)
  if (!latestVersion?.id) {
    ElMessage.warning('暂无可用版本')
    return
  }
  const formats = resolveDownloadFormats(file, latestVersion)
  const selectedFormat = format || formats[0]
  if (!selectedFormat) {
    ElMessage.warning('暂无可用下载格式')
    return
  }
  const isOriginal = resolveIsOriginalDownloadFormat(file, selectedFormat, latestVersion)
  const url = await getShareResourceUrl({
    token,
    session: shareSession,
    accessSession: publicAccessSession,
    kind: isOriginal ? 'download_original' : 'download_converted',
    fileId: file.id,
    versionId: latestVersion.id,
    format: isOriginal ? undefined : selectedFormat,
  })
  downloadViaIframe(url)
}

function goHome() {
  router.push('/')
}

async function submitUnlock() {
  const password = String(unlockPassword.value || '')
  if (!password.trim()) {
    unlockError.value = '请输入分享密码'
    return
  }

  unlocking.value = true
  unlockError.value = ''
  try {
    if (unlockMode.value === 'resource') {
      await publicAccessSession.unlock(password)
    } else {
      await shareSession.unlock(password)
    }
    unlockRequired.value = false
    unlockPassword.value = ''
    await fetchProject()
  } catch (err) {
    unlockError.value = getUnlockErrorMessage(err)
  } finally {
    unlocking.value = false
  }
}

async function fetchProject() {
  loading.value = true
  error.value = ''
  try {
    const data = await getShareProject(token, {
      headers: buildAccessHeaders(),
    })
    unlockRequired.value = false
    unlockMode.value = 'share'
    unlockError.value = ''
    project.value = data.project || data
    files.value = data.files || []
    folders.value = data.folders || []
    shareInfo.value = { ...DEFAULT_SHARE_PERMISSIONS, ...(data.share || {}) }
    if (
      currentFolderId.value !== null &&
      currentFolderId.value !== '' &&
      !folders.value.some((folder) => folder.id === currentFolderId.value)
    ) {
      currentFolderId.value = ''
    }
  } catch (err) {
    if (isSharePasswordRequiredError(err)) {
      unlockRequired.value = true
      unlockMode.value = 'share'
      error.value = ''
      return
    }
    if (isResourcePasswordRequiredError(err)) {
      unlockRequired.value = true
      unlockMode.value = 'resource'
      error.value = ''
      return
    }
    const detail = err?.response?.data?.detail
    if (detail === 'login_required') {
      error.value = '请先登录后访问该公开资源'
    } else if (detail === 'group_required') {
      error.value = '当前账号不在允许访问的用户组中'
    } else {
      error.value = '项目不存在或访问令牌无效'
    }
  } finally {
    loading.value = false
  }
}

function clearPublicAccessHeartbeat() {
  if (publicAccessHeartbeatTimer) {
    clearInterval(publicAccessHeartbeatTimer)
    publicAccessHeartbeatTimer = null
  }
}

function startPublicAccessHeartbeat() {
  clearPublicAccessHeartbeat()
  if (typeof window === 'undefined') return
  if (!publicAccessSession.grantToken.value) return
  publicAccessHeartbeatTimer = window.setInterval(() => {
    publicAccessSession.heartbeat().catch(() => {})
  }, 30000)
}

function releasePublicAccessOnPageHide() {
  publicAccessSession.releaseOnPageHide?.()
}

onMounted(() => {
  fetchProject()
  if (typeof window !== 'undefined') {
    window.addEventListener('pagehide', releasePublicAccessOnPageHide)
    window.addEventListener('beforeunload', releasePublicAccessOnPageHide)
  }
})

watch(() => publicAccessSession.grantToken.value, () => {
  startPublicAccessHeartbeat()
}, { immediate: true })

onBeforeUnmount(() => {
  clearPublicAccessHeartbeat()
  if (typeof window !== 'undefined') {
    window.removeEventListener('pagehide', releasePublicAccessOnPageHide)
    window.removeEventListener('beforeunload', releasePublicAccessOnPageHide)
  }
})
</script>

<style scoped>
.share-project {
  animation: fadeIn 160ms ease;
}

.project-info-card,
.file-list-card,
.error-card,
.unlock-card {
  border-radius: 12px;
  background-color: rgba(255, 255, 255, 0.94);
  border: 1px solid var(--border-color-light, #e4e9f0);
}

.project-info-card,
.file-list-card {
  margin-bottom: 20px;
}

.unlock-card {
  margin-bottom: 20px;
}

.project-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary, #0f172a);
  margin: 0 0 8px 0;
}

.project-title--mobile {
  margin-bottom: 0;
}

.project-desc {
  color: var(--text-secondary, #64748b);
  font-size: 14px;
  margin: 0;
}

.card-header,
.resource-toolbar,
.resource-breadcrumb,
.action-buttons,
.resource-meta-cell,
.resource-copy {
  display: flex;
}

.card-header {
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-weight: 700;
  color: var(--text-primary, #0f172a);
}

.file-search-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 14px;
}

.resource-toolbar {
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.resource-breadcrumb {
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.folder-root-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: var(--text-secondary, #475569);
  cursor: pointer;
  padding: 0;
  font-weight: 700;
}

.folder-root-btn--active {
  color: var(--color-primary, #1a5276);
}

.folder-current-name {
  color: var(--text-secondary, #64748b);
  font-weight: 700;
}

.file-table {
  width: 100%;
}

.resource-name-cell {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.resource-name-cell--folder {
  cursor: pointer;
}

.resource-icon {
  margin-top: 2px;
  color: #2563eb;
}

.resource-name-cell--folder .resource-icon {
  color: #d97706;
}

.resource-copy {
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}

.resource-copy > span {
  font-weight: 700;
  color: #0f172a;
  word-break: break-word;
}

.resource-copy > small,
.resource-meta-cell > small {
  color: #64748b;
  line-height: 1.4;
}

.resource-meta-cell {
  flex-direction: column;
  gap: 4px;
  color: #334155;
}

.action-buttons {
  flex-wrap: wrap;
  gap: 8px;
}

.action-btn {
  margin-left: 0;
}

.mobile-changelog {
  color: #475569;
}

.unlock-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.unlock-copy {
  margin: 0;
  color: #475569;
  line-height: 1.6;
}

.unlock-error {
  margin: 0;
  color: #dc2626;
  font-size: 13px;
}

.unlock-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.share-project-mobile-shell {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.share-project-mobile-shell__hero,
.share-project-mobile-resource-head {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.share-project-mobile-shell__eyebrow,
.share-project-mobile-resource-head__eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #2563eb;
}

.share-project-mobile-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.share-project-mobile-stat {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
}

.share-project-mobile-details {
  border-top: 1px solid rgba(226, 232, 240, 0.9);
  padding-top: 10px;
}

.share-project-mobile-details summary {
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.share-project-mobile-details[open] .project-desc {
  margin-top: 10px;
}

.share-project-mobile-resource-head {
  flex-direction: row;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.share-project-mobile-resource-head__title {
  margin-top: 2px;
  color: #0f172a;
  font-size: 18px;
  font-weight: 700;
}

.file-list-card :deep(.file-list-card__icon--folder) {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.14), rgba(251, 191, 36, 0.2));
  color: #b45309;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 767px) {
  .project-info-card--mobile-shell,
  .file-list-card--mobile-shell {
    border-radius: 18px;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.94));
    box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
  }

  .resource-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .resource-breadcrumb {
    width: 100%;
    overflow: visible;
    flex-wrap: wrap;
    row-gap: 8px;
    padding-bottom: 2px;
    white-space: normal;
  }

  .folder-root-btn {
    max-width: 100%;
    padding: 8px 12px;
    border-radius: 999px;
    background: rgba(226, 232, 240, 0.55);
    white-space: normal;
  }

  .folder-current-name {
    flex: 1 1 100%;
    max-width: 100%;
    white-space: normal;
    word-break: break-word;
  }

  .folder-root-btn--active {
    background: rgba(37, 99, 235, 0.1);
  }

  .file-search-bar {
    margin-bottom: 12px;
  }

  .share-project-mobile-resource-head {
    position: sticky;
    top: calc(8px + env(safe-area-inset-top));
    z-index: 4;
    padding: 12px 14px;
    border: 1px solid rgba(226, 232, 240, 0.92);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.94);
    backdrop-filter: blur(14px);
  }
}
</style>
