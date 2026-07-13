-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 文档元信息表
CREATE TABLE IF NOT EXISTS documents (
    id          SERIAL PRIMARY KEY,
    filename    TEXT NOT NULL,
    doc_type    TEXT NOT NULL DEFAULT 'regulation',
    source      TEXT,
    page_count  INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 文档分块 + 向量表（512 维，对应 bge-small-zh-v1.5）
CREATE TABLE IF NOT EXISTS document_chunks (
    id          SERIAL PRIMARY KEY,
    doc_id      INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',
    embedding   vector(512),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 向量索引（数据量 < 10 万时 ivfflat 足够）
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON document_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON document_chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_metadata ON document_chunks USING gin(metadata);

-- BadCase 反馈表（供 LoRA 数据闭环）
CREATE TABLE IF NOT EXISTS feedback (
    id          SERIAL PRIMARY KEY,
    question    TEXT NOT NULL,
    answer      TEXT,
    model       TEXT DEFAULT 'base',
    sources     JSONB DEFAULT '[]',
    rating      TEXT CHECK (rating IN ('good', 'bad')),
    note        TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
