import type { ModelType, SourceItem } from '../api/client'
import { API_BASE, API_KEY } from '../api/client'

export interface SSEHandlers {
  onRetrieval?: (sources: SourceItem[]) => void
  onToken?: (text: string) => void
  onDone?: (latencyMs: number) => void
  onError?: (message: string) => void
}

export interface AskStreamOptions {
  question: string
  model?: ModelType
  docType?: string
  signal?: AbortSignal
}

/**
 * 通过 POST + ReadableStream 解析 SSE 流式响应。
 */
export async function askStream(
  options: AskStreamOptions,
  handlers: SSEHandlers,
): Promise<void> {
  const { question, model = 'base', docType, signal } = options

  const body: Record<string, string> = { question, model }
  if (docType) body.doc_type = docType

  const res = await fetch(`${API_BASE}/api/ask/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY,
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `请求失败 (${res.status})`)
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('无法读取流式响应')

  const decoder = new TextDecoder()
  let buffer = ''
  let eventType = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true }).replace(/\r/g, '')
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    parseSSELines(lines, (type) => { eventType = type }, () => eventType, handlers)
  }

  if (buffer.trim()) {
    parseSSELines([buffer], (type) => { eventType = type }, () => eventType, handlers)
  }
}

function parseSSELines(
  lines: string[],
  setEventType: (type: string) => void,
  getEventType: () => string,
  handlers: SSEHandlers,
) {
  for (const line of lines) {
    if (!line.trim()) {
      setEventType('')
      continue
    }
    if (line.startsWith('event:')) {
      setEventType(line.slice(6).trim())
    } else if (line.startsWith('data:')) {
      const raw = line.slice(5).trim()
      if (!raw) continue
      try {
        const data = JSON.parse(raw) as Record<string, unknown>
        const resolved = resolveEventType(getEventType(), data)
        dispatchSSE(resolved, data, handlers)
      } catch {
        /* 忽略解析失败的行 */
      }
    }
  }
}

function resolveEventType(eventType: string, data: Record<string, unknown>): string {
  if (eventType) return eventType
  if (typeof data.text === 'string') return 'token'
  if (Array.isArray(data.sources)) return 'retrieval'
  if ('latency_ms' in data) return 'done'
  if (typeof data.message === 'string') return 'error'
  return ''
}

function dispatchSSE(eventType: string, data: Record<string, unknown>, handlers: SSEHandlers) {
  switch (eventType) {
    case 'retrieval':
      handlers.onRetrieval?.(data.sources as SourceItem[])
      break
    case 'token':
      handlers.onToken?.(data.text as string)
      break
    case 'done':
      handlers.onDone?.(data.latency_ms as number)
      break
    case 'error':
      handlers.onError?.(data.message as string)
      break
  }
}
