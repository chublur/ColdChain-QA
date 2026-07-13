<script setup lang="ts">
import type { ModelType } from '../api/client'

const model = defineModel<ModelType>({ required: true })

const docType = defineModel<string>('docType', { default: '' })

const docTypes = [
  { value: '', label: '全部文档' },
  { value: 'regulation', label: '法规标准' },
  { value: 'sop', label: 'SOP 流程' },
  { value: 'equipment', label: '设备验证' },
]
</script>

<template>
  <div class="model-switch">
    <div class="switch-group">
      <label class="label">推理模型</label>
      <div class="toggle">
        <button
          :class="{ active: model === 'base' }"
          @click="model = 'base'"
        >
          Base
          <span class="desc">Qwen2.5-3B</span>
        </button>
        <button
          :class="{ active: model === 'lora' }"
          @click="model = 'lora'"
        >
          LoRA
          <span class="desc">微调版</span>
        </button>
      </div>
    </div>

    <div class="switch-group">
      <label class="label">检索范围</label>
      <select v-model="docType" class="select">
        <option v-for="dt in docTypes" :key="dt.value" :value="dt.value">
          {{ dt.label }}
        </option>
      </select>
    </div>
  </div>
</template>

<style scoped>
.model-switch {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.4rem;
  display: block;
}

.toggle {
  display: flex;
  background: var(--color-bg);
  border-radius: var(--radius);
  padding: 3px;
  border: 1px solid var(--color-border);
}

.toggle button {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-muted);
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
}

.toggle button .desc {
  font-size: 0.65rem;
  font-weight: 400;
  opacity: 0.7;
}

.toggle button.active {
  background: var(--color-surface);
  color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.select {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 0.85rem;
  outline: none;
}

.select:focus {
  border-color: var(--color-accent);
}
</style>
