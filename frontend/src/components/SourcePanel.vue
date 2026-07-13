<script setup lang="ts">
import type { SourceItem } from '../api/client'

defineProps<{
  sources: SourceItem[]
}>()
</script>

<template>
  <div class="source-panel">
    <h3 class="panel-title">
      <span class="icon">📚</span>
      引用来源
    </h3>

    <div v-if="sources.length === 0" class="empty">
      提问后将展示检索到的法规 / SOP 文档片段
    </div>

    <div v-else class="source-list">
      <div v-for="(src, i) in sources" :key="i" class="source-card">
        <div class="source-header">
          <span class="source-name">{{ src.source || '未知来源' }}</span>
          <span class="source-page">P{{ src.page }}</span>
          <span class="source-score">{{ (src.score * 100).toFixed(0) }}%</span>
        </div>
        <p class="source-content">{{ src.content }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.source-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-primary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  flex-shrink: 0;
}

.empty {
  color: var(--color-text-muted);
  font-size: 0.85rem;
  text-align: center;
  padding: 2rem 1rem;
  background: var(--color-bg);
  border-radius: var(--radius);
  border: 1px dashed var(--color-border);
}

.source-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.source-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0.75rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.source-card:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-sm);
}

.source-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
}

.source-name {
  font-weight: 600;
  color: var(--color-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-page {
  color: var(--color-text-muted);
}

.source-score {
  background: var(--color-accent-soft);
  color: var(--color-primary);
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-weight: 500;
}

.source-content {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
