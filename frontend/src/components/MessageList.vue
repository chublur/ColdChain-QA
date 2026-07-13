<script setup lang="ts">
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: import('../api/client').SourceItem[]
  latencyMs?: number
  model?: string
  streaming?: boolean
}

defineProps<{
  messages: ChatMessage[]
}>()

const emit = defineEmits<{
  feedback: [msg: ChatMessage, rating: 'good' | 'bad']
}>()

function formatContent(text: string): string {
  return text
    .replace(/【结论】/g, '<strong class="tag tag-conclusion">【结论】</strong>')
    .replace(/【依据】/g, '<strong class="tag tag-basis">【依据】</strong>')
    .replace(/【处置建议】/g, '<strong class="tag tag-action">【处置建议】</strong>')
    .replace(/\n/g, '<br/>')
}
</script>

<template>
  <div class="message-list">
    <div v-if="messages.length === 0" class="welcome">
      <div class="welcome-icon">❄️</div>
      <h2>医药冷链合规智能顾问</h2>
      <p>基于 GSP / 国标知识库，为您提供温度管控、法规引用与 SOP 处置建议</p>
      <div class="suggestions">
        <span class="hint">试试这些问题：</span>
        <ul>
          <li>疫苗冷链运输温度范围是多少？</li>
          <li>GSP 对冷藏药品储存有什么要求？</li>
          <li>运输途中温度超标应如何处理？</li>
        </ul>
      </div>
    </div>

    <div
      v-for="msg in messages"
      :key="msg.id"
      class="message"
      :class="msg.role"
    >
      <div class="avatar">
        <span v-if="msg.role === 'user'">👤</span>
        <span v-else>🤖</span>
      </div>
      <div class="bubble">
        <div
          v-if="msg.role === 'assistant'"
          class="content"
          v-html="formatContent(msg.content)"
        />
        <div v-else class="content">{{ msg.content }}</div>

        <div v-if="msg.streaming && !msg.content" class="typing">
          <span /><span /><span />
        </div>

        <div v-if="msg.role === 'assistant' && !msg.streaming && msg.content" class="meta">
          <span v-if="msg.latencyMs" class="latency">{{ msg.latencyMs }}ms</span>
          <span v-if="msg.model" class="model-tag">{{ msg.model === 'lora' ? 'LoRA' : 'Base' }}</span>
          <div class="feedback-btns">
            <button title="回答有帮助" @click="emit('feedback', msg, 'good')">👍</button>
            <button title="回答需改进" @click="emit('feedback', msg, 'bad')">👎</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.welcome {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--color-text-muted);
}

.welcome-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.welcome h2 {
  color: var(--color-primary);
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
}

.suggestions {
  margin-top: 2rem;
  text-align: left;
  max-width: 400px;
  margin-inline: auto;
  background: var(--color-surface);
  padding: 1rem 1.25rem;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
}

.suggestions .hint {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.suggestions ul {
  list-style: none;
  margin-top: 0.5rem;
}

.suggestions li {
  padding: 0.4rem 0;
  font-size: 0.9rem;
  color: var(--color-primary-light);
  cursor: default;
}

.suggestions li::before {
  content: '› ';
  color: var(--color-accent);
}

.message {
  display: flex;
  gap: 0.75rem;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message .avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.message.assistant .avatar {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  border: none;
}

.bubble {
  padding: 0.875rem 1.125rem;
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border);
}

.message.user .bubble {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  color: #fff;
  border: none;
}

.content {
  font-size: 0.95rem;
  line-height: 1.7;
  word-break: break-word;
}

.content :deep(.tag) {
  display: inline-block;
  margin-right: 0.25rem;
}

.content :deep(.tag-conclusion) { color: var(--color-primary); }
.content :deep(.tag-basis) { color: #7c3aed; }
.content :deep(.tag-action) { color: var(--color-success); }

.message.user .content :deep(.tag) {
  color: inherit;
}

.typing {
  display: flex;
  gap: 4px;
  margin-top: 0.5rem;
}

.typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: bounce 1.2s infinite;
}

.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-6px); opacity: 1; }
}

.meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--color-border);
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.latency, .model-tag {
  background: var(--color-bg);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.feedback-btns {
  margin-left: auto;
  display: flex;
  gap: 0.25rem;
}

.feedback-btns button {
  padding: 0.2rem 0.5rem;
  border-radius: 6px;
  font-size: 1rem;
  transition: background 0.2s;
}

.feedback-btns button:hover {
  background: var(--color-bg);
}
</style>
