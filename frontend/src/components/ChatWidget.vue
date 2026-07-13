<script setup lang="ts">
import { ref, nextTick, computed } from 'vue'
import type { ModelType, SourceItem } from '../api/client'
import { submitFeedback } from '../api/client'
import { askStream } from '../composables/useSSE'
import MessageList, { type ChatMessage } from './MessageList.vue'

const props = defineProps<{
  model: ModelType
  docType: string
}>()

const emit = defineEmits<{
  speaking: [boolean]
  status: [string]
  sources: [SourceItem[]]
}>()

const messages = ref<ChatMessage[]>([])
const input = ref('')
const loading = ref(false)
let abortController: AbortController | null = null

const canSend = computed(() => input.value.trim().length > 0 && !loading.value)

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

async function scrollToBottom() {
  await nextTick()
  const el = document.querySelector('.message-list')
  if (el) el.scrollTop = el.scrollHeight
}

async function send() {
  const question = input.value.trim()
  if (!question || loading.value) return

  input.value = ''
  loading.value = true
  emit('sources', [])
  emit('speaking', true)
  emit('status', '正在检索知识库…')

  const assistantId = uid()
  messages.value.push(
    { id: uid(), role: 'user', content: question },
    {
      id: assistantId,
      role: 'assistant',
      content: '',
      streaming: true,
      model: props.model,
    },
  )
  await scrollToBottom()

  /** 必须通过响应式数组下标更新，直接改 push 前的普通对象不会触发视图更新 */
  function withAssistant(mutator: (msg: ChatMessage) => void) {
    const idx = messages.value.findIndex((m) => m.id === assistantId)
    if (idx !== -1) mutator(messages.value[idx])
  }

  abortController = new AbortController()

  try {
    await askStream(
      {
        question,
        model: props.model,
        docType: props.docType || undefined,
        signal: abortController.signal,
      },
      {
        onRetrieval: (srcs) => {
          withAssistant((msg) => { msg.sources = srcs })
          emit('sources', srcs)
          emit('status', '正在生成回答…')
        },
        onToken: (text) => {
          withAssistant((msg) => { msg.content += text })
          scrollToBottom()
        },
        onDone: (latencyMs) => {
          withAssistant((msg) => {
            msg.latencyMs = latencyMs
            msg.streaming = false
          })
          loading.value = false
          emit('speaking', false)
          emit('status', '在线待命')
        },
        onError: (message) => {
          withAssistant((msg) => {
            msg.content = `⚠️ ${message}`
            msg.streaming = false
          })
          loading.value = false
          emit('speaking', false)
          emit('status', '出现错误')
        },
      },
    )
    // 流结束兜底：避免 done 事件漏解析时一直卡在加载动画
    withAssistant((msg) => {
      if (msg.streaming) msg.streaming = false
    })
    if (loading.value) {
      loading.value = false
      emit('speaking', false)
      emit('status', '在线待命')
    }
  } catch (e) {
    withAssistant((msg) => {
      if ((e as Error).name !== 'AbortError') {
        msg.content = `⚠️ ${(e as Error).message}`
      }
      msg.streaming = false
    })
    loading.value = false
    emit('speaking', false)
    emit('status', '在线待命')
  }
}

function stop() {
  abortController?.abort()
  loading.value = false
  const last = messages.value.at(-1)
  if (last?.streaming) {
    last.streaming = false
    if (!last.content) last.content = '（已停止生成）'
  }
  emit('speaking', false)
  emit('status', '在线待命')
}

async function onFeedback(msg: ChatMessage, rating: 'good' | 'bad') {
  const idx = messages.value.findIndex((m) => m.id === msg.id)
  const question = idx > 0 ? messages.value[idx - 1]?.content : ''
  try {
    await submitFeedback({
      question,
      answer: msg.content,
      model: msg.model || props.model,
      rating,
      sources: msg.sources || [],
    })
    emit('status', rating === 'good' ? '感谢反馈！' : '已记录，将用于改进')
    setTimeout(() => emit('status', '在线待命'), 2000)
  } catch {
    emit('status', '反馈提交失败')
  }
}

defineExpose({})
</script>

<template>
  <div class="chat-widget">
    <MessageList
      :messages="messages"
      @feedback="onFeedback"
    />

    <div class="input-area">
      <textarea
        v-model="input"
        placeholder="输入冷链合规问题，如：疫苗运输温度范围？"
        rows="2"
        :disabled="loading"
        @keydown.enter.exact.prevent="send"
      />
      <div class="input-actions">
        <span class="hint">Enter 发送 · Shift+Enter 换行</span>
        <button v-if="loading" class="btn btn-stop" @click="stop">停止</button>
        <button v-else class="btn btn-send" :disabled="!canSend" @click="send">
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-widget {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.input-area {
  padding: 1rem 1.5rem 1.25rem;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
  flex-shrink: 0;
}

textarea {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  resize: none;
  font-size: 0.95rem;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: var(--color-bg);
}

textarea:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.15);
}

textarea:disabled {
  opacity: 0.7;
}

.input-actions {
  display: flex;
  align-items: center;
  margin-top: 0.5rem;
  gap: 0.75rem;
}

.hint {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  flex: 1;
}

.btn {
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius);
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-send {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  color: #fff;
}

.btn-send:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-stop {
  background: var(--color-danger);
  color: #fff;
}
</style>
