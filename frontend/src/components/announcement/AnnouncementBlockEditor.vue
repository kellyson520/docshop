<template>
  <section class="announcement-block-editor">
    <div class="block-toolbar">
      <el-button
        size="small"
        data-testid="add-block-paragraph"
        @click="addBlock('paragraph')"
      >
        添加段落
      </el-button>
      <el-button size="small" @click="addBlock('code')">添加代码</el-button>
      <el-button size="small" @click="addBlock('button')">添加按钮</el-button>
      <el-button size="small" @click="addBlock('image')">添加图片</el-button>
      <el-button size="small" @click="addBlock('video')">添加视频</el-button>
    </div>

    <div v-if="!localBlocks.length" class="empty-state">
      暂无内容块，点击上方按钮开始编辑。
    </div>

    <div
      v-for="(block, index) in localBlocks"
      :key="`${block.type}-${index}`"
      class="block-item"
    >
      <div class="block-item__header">
        <strong>{{ blockTypeLabel(block.type) }} {{ index + 1 }}</strong>
        <div class="block-item__actions">
          <button type="button" class="text-action" :disabled="index === 0" @click="moveBlock(index, -1)">
            上移
          </button>
          <button
            type="button"
            class="text-action"
            :disabled="index === localBlocks.length - 1"
            @click="moveBlock(index, 1)"
          >
            下移
          </button>
          <button type="button" class="text-action text-action--danger" @click="removeBlock(index)">
            删除
          </button>
        </div>
      </div>

      <label class="field-label">
        类型
        <select v-model="block.type" class="native-select" @change="handleTypeChange(index)">
          <option value="paragraph">段落</option>
          <option value="code">代码</option>
          <option value="button">按钮</option>
          <option value="image">图片</option>
          <option value="video">视频</option>
        </select>
      </label>

      <template v-if="block.type === 'paragraph'">
        <el-form-item label="段落内容">
          <el-input v-model="block.text" type="textarea" :rows="3" @input="emitBlocks" />
        </el-form-item>
      </template>

      <template v-else-if="block.type === 'code'">
        <div class="block-grid">
          <el-form-item label="语言">
            <el-input v-model="block.language" placeholder="bash / json / js" @input="emitBlocks" />
          </el-form-item>
        </div>
        <el-form-item label="代码内容">
          <el-input v-model="block.content" type="textarea" :rows="4" @input="emitBlocks" />
        </el-form-item>
      </template>

      <template v-else-if="block.type === 'button'">
        <div class="block-grid">
          <el-form-item label="按钮文案">
            <el-input v-model="block.label" @input="emitBlocks" />
          </el-form-item>
          <el-form-item label="链接">
            <el-input v-model="block.url" @input="emitBlocks" />
          </el-form-item>
        </div>
      </template>

      <template v-else-if="block.type === 'image' || block.type === 'video'">
        <div class="block-grid">
          <el-form-item label="文件 ID">
            <el-input v-model="block.file_id" @input="emitBlocks" />
          </el-form-item>
          <el-form-item label="说明">
            <el-input v-model="block.caption" @input="emitBlocks" />
          </el-form-item>
        </div>
      </template>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update:modelValue'])

const localBlocks = computed({
  get: () => Array.isArray(props.modelValue) ? props.modelValue : [],
  set: (value) => emit('update:modelValue', value),
})

function createBlock(type = 'paragraph') {
  switch (type) {
    case 'code':
      return { type: 'code', language: 'bash', content: '' }
    case 'button':
      return { type: 'button', label: '', url: '' }
    case 'image':
      return { type: 'image', file_id: '', caption: '' }
    case 'video':
      return { type: 'video', file_id: '', caption: '' }
    case 'paragraph':
    default:
      return { type: 'paragraph', text: '' }
  }
}

function normalizeBlock(block = {}) {
  return {
    ...createBlock(block.type || 'paragraph'),
    ...block,
  }
}

function emitBlocks() {
  localBlocks.value = [...localBlocks.value]
}

function addBlock(type) {
  localBlocks.value = [...localBlocks.value, createBlock(type)]
}

function removeBlock(index) {
  const next = [...localBlocks.value]
  next.splice(index, 1)
  localBlocks.value = next
}

function moveBlock(index, offset) {
  const targetIndex = index + offset
  if (targetIndex < 0 || targetIndex >= localBlocks.value.length) return

  const next = [...localBlocks.value]
  const [item] = next.splice(index, 1)
  next.splice(targetIndex, 0, item)
  localBlocks.value = next
}

function handleTypeChange(index) {
  const next = [...localBlocks.value]
  next[index] = normalizeBlock({ type: next[index]?.type })
  localBlocks.value = next
}

function blockTypeLabel(type) {
  return {
    paragraph: '段落',
    code: '代码',
    button: '按钮',
    image: '图片',
    video: '视频',
  }[type] || type
}
</script>

<style scoped>
.announcement-block-editor {
  display: grid;
  gap: 12px;
}

.block-toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.empty-state {
  padding: 16px;
  border: 1px dashed #cbd5e1;
  border-radius: 14px;
  background: #f8fafc;
  color: #64748b;
  font-size: 13px;
}

.block-item {
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
}

.block-item__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}

.block-item__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.block-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.field-label {
  display: grid;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.native-select {
  width: 100%;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid #d0d5dd;
  border-radius: 10px;
  background: #fff;
  color: #172033;
}

.text-action {
  padding: 0;
  border: 0;
  background: transparent;
  color: #2563eb;
  cursor: pointer;
  font-size: 13px;
}

.text-action:disabled {
  cursor: not-allowed;
  color: #94a3b8;
}

.text-action--danger {
  color: #dc2626;
}

@media (max-width: 768px) {
  .block-item__header,
  .block-grid {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
