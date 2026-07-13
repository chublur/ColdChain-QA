<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { DocumentItem } from '../api/client'
import { fetchDocuments, uploadDocument, deleteDocument } from '../api/client'

const emit = defineEmits<{ updated: [] }>()

const documents = ref<DocumentItem[]>([])
const loading = ref(false)
const uploading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    documents.value = await fetchDocuments()
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploading.value = true
  error.value = ''
  try {
    await uploadDocument(file)
    await load()
    emit('updated')
  } catch (err) {
    error.value = (err as Error).message
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function remove(doc: DocumentItem) {
  if (!confirm(`确定删除「${doc.filename}」？`)) return
  try {
    await deleteDocument(doc.id)
    await load()
    emit('updated')
  } catch (err) {
    error.value = (err as Error).message
  }
}

const typeLabels: Record<string, string> = {
  regulation: '法规',
  sop: 'SOP',
  equipment: '设备',
}

onMounted(load)

defineExpose({ reload: load })
</script>

<template>
  <div class="doc-manager">
    <div class="header">
      <h3>知识库</h3>
      <label class="upload-btn" :class="{ disabled: uploading }">
        <input type="file" accept=".pdf,.docx,.txt,.md" hidden @change="onFileChange" />
        {{ uploading ? '上传中…' : '+ 上传' }}
      </label>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="loading" class="loading">加载中…</div>

    <div v-else-if="documents.length === 0" class="empty">
      暂无文档，请上传冷链法规 PDF / Word / 文本
    </div>

    <ul v-else class="doc-list">
      <li v-for="doc in documents" :key="doc.id" class="doc-item">
        <div class="doc-info">
          <span class="doc-name" :title="doc.filename">{{ doc.filename }}</span>
          <span class="doc-meta">
            <span class="badge">{{ typeLabels[doc.doc_type] || doc.doc_type }}</span>
            {{ doc.chunk_count }} 块
          </span>
        </div>
        <button class="delete-btn" title="删除" @click="remove(doc)">×</button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.doc-manager {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header h3 {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-primary);
}

.upload-btn {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-primary-light);
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  background: var(--color-accent-soft);
  transition: opacity 0.2s;
}

.upload-btn:hover:not(.disabled) {
  opacity: 0.85;
}

.upload-btn.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  font-size: 0.8rem;
  color: var(--color-danger);
}

.loading, .empty {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  text-align: center;
  padding: 1rem;
}

.doc-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 0.8rem;
}

.doc-info {
  flex: 1;
  min-width: 0;
}

.doc-name {
  display: block;
  font-weight: 500;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-meta {
  color: var(--color-text-muted);
  font-size: 0.75rem;
}

.badge {
  background: var(--color-accent-soft);
  color: var(--color-primary);
  padding: 0.05rem 0.35rem;
  border-radius: 3px;
  margin-right: 0.35rem;
}

.delete-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: var(--color-text-muted);
  font-size: 1.1rem;
  line-height: 1;
  transition: all 0.2s;
}

.delete-btn:hover {
  background: #fee2e2;
  color: var(--color-danger);
}
</style>
