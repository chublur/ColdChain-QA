<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { ModelType, SourceItem } from './api/client'
import { fetchHealth, type HealthStatus } from './api/client'
import ChatWidget from './components/ChatWidget.vue'
import SourcePanel from './components/SourcePanel.vue'
import ModelSwitch from './components/ModelSwitch.vue'
import DocManager from './components/DocManager.vue'
import AvatarPanel from './components/AvatarPanel.vue'

const model = ref<ModelType>('base')
const docType = ref('')
const health = ref<HealthStatus | null>(null)
const speaking = ref(false)
const statusText = ref('在线待命')
const sources = ref<SourceItem[]>([])
const docManagerRef = ref<InstanceType<typeof DocManager> | null>(null)

async function loadHealth() {
  try {
    health.value = await fetchHealth()
  } catch {
    health.value = null
  }
}

function onDocUpdated() {
  loadHealth()
}

onMounted(loadHealth)
</script>

<template>
  <div class="app">
    <header class="header">
      <div class="brand">
        <div class="logo">❄</div>
        <div>
          <h1>冷链物流智能问答系统</h1>
          <p>医药冷链合规 · RAG + LoRA</p>
        </div>
      </div>
      <div class="header-status">
        <span
          class="status-dot"
          :class="health?.status === 'ok' ? 'ok' : 'warn'"
        />
        <span class="status-text">
          {{ health ? `${health.kb.documents} 文档 · ${health.kb.chunks} 块` : '连接中…' }}
        </span>
      </div>
    </header>

    <main class="main">
      <aside class="sidebar left">
        <DocManager ref="docManagerRef" @updated="onDocUpdated" />
        <div class="divider" />
        <ModelSwitch v-model="model" v-model:doc-type="docType" />
      </aside>

      <section class="chat-section">
        <ChatWidget
          :model="model"
          :doc-type="docType"
          @speaking="speaking = $event"
          @status="statusText = $event"
          @sources="sources = $event"
        />
      </section>

      <aside class="sidebar right">
        <AvatarPanel :speaking="speaking" :status-text="statusText" />
        <div class="divider" />
        <SourcePanel :sources="sources" />
      </aside>
    </main>

    <footer class="footer">
      ColdChain-QA · 基于 pgvector 混合检索 + Qwen2.5-3B 本地推理
    </footer>
  </div>
</template>

<style scoped>
.app {
  height: 100%;
  display: flex;
  flex-direction: column;
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 1rem;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 0;
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.logo {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  box-shadow: var(--shadow-md);
}

.brand h1 {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--color-primary);
}

.brand p {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.header-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  background: var(--color-surface);
  padding: 0.4rem 0.875rem;
  border-radius: 20px;
  border: 1px solid var(--color-border);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-muted);
}

.status-dot.ok { background: var(--color-success); }
.status-dot.warn { background: #f59e0b; }

.main {
  flex: 1;
  display: grid;
  grid-template-columns: 240px 1fr 280px;
  gap: 1rem;
  min-height: 0;
  padding-bottom: 0.5rem;
}

.sidebar {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-section {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.divider {
  height: 1px;
  background: var(--color-border);
  margin: 1rem 0;
  flex-shrink: 0;
}

.footer {
  text-align: center;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  padding: 0.75rem;
  flex-shrink: 0;
}

@media (max-width: 1024px) {
  .main {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
  }

  .sidebar.left {
    order: 2;
    max-height: 200px;
  }

  .chat-section {
    order: 1;
    min-height: 60vh;
  }

  .sidebar.right {
    order: 3;
    max-height: 280px;
  }
}
</style>
