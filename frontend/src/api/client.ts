export type ModelType = 'base' | 'lora'
export type DocType = 'regulation' | 'sop' | 'equipment' | ''

export interface SourceItem {
  content: string
  source: string
  page: string | number
  score: number
}

export interface HealthStatus {
  status: string
  app: string
  version?: string
  kb: { documents: number; chunks: number }
  postgres?: { status: string }
  ollama?: { status: string; base_ready?: boolean; lora_ready?: boolean }
}

export interface DocumentItem {
  id: number
  filename: string
  doc_type: string
  page_count: number
  chunk_count: number
  created_at: string | null
}

const API_BASE = import.meta.env.VITE_API_BASE || ''
const API_KEY = import.meta.env.VITE_API_KEY || 'change-me-in-production'

function headers(json = true): HeadersInit {
  const h: Record<string, string> = { 'x-api-key': API_KEY }
  if (json) h['Content-Type'] = 'application/json'
  return h
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) throw new Error('健康检查失败')
  return res.json()
}

export async function fetchDocuments(): Promise<DocumentItem[]> {
  const res = await fetch(`${API_BASE}/api/documents`, { headers: headers(false) })
  if (!res.ok) throw new Error('获取文档列表失败')
  const data = await res.json()
  return data.documents
}

export async function uploadDocument(file: File): Promise<{ doc_id: number; chunks: number }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/api/ingest`, {
    method: 'POST',
    headers: { 'x-api-key': API_KEY },
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '上传失败')
  }
  return res.json()
}

export async function deleteDocument(docId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
    method: 'DELETE',
    headers: headers(false),
  })
  if (!res.ok) throw new Error('删除失败')
}

export async function submitFeedback(payload: {
  question: string
  answer: string
  model: string
  rating: 'good' | 'bad'
  sources: SourceItem[]
  note?: string
}): Promise<void> {
  const res = await fetch(`${API_BASE}/api/feedback`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error('反馈提交失败')
}

export { API_BASE, API_KEY }
