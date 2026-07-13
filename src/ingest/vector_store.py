"""pgvector 向量存储封装。"""
import json
import logging
from typing import List, Dict, Any, Optional

import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None
_embeddings = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def get_embeddings():
    """懒加载 Embedding 模型，默认 CPU 推理节省显存。"""
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": settings.EMBEDDING_DEVICE},
            encode_kwargs={"normalize_embeddings": True},
        )
        logger.info("Embedding 模型已加载: %s (%s)", settings.EMBEDDING_MODEL, settings.EMBEDDING_DEVICE)
    return _embeddings


def embed_texts(texts: List[str]) -> List[List[float]]:
    """批量文本向量化。"""
    return get_embeddings().embed_documents(texts)


def format_embedding(vec: List[float]) -> str:
    """将向量格式化为 pgvector 可接受的字符串。"""
    return "[" + ",".join(str(v) for v in vec) + "]"


def insert_document(
    filename: str,
    doc_type: str,
    page_count: int,
    chunks: List[Dict[str, Any]],
    source: str = "",
) -> int:
    """
    将文档及其分块写入 pgvector。

    Returns:
        doc_id
    """
    session = get_session()
    try:
        result = session.execute(
            text("""
                INSERT INTO documents (filename, doc_type, source, page_count)
                VALUES (:filename, :doc_type, :source, :page_count)
                RETURNING id
            """),
            {
                "filename": filename,
                "doc_type": doc_type,
                "source": source,
                "page_count": page_count,
            },
        )
        doc_id = result.scalar_one()

        contents = [c["content"] for c in chunks]
        vectors = embed_texts(contents)

        for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
            session.execute(
                text("""
                    INSERT INTO document_chunks
                        (doc_id, chunk_index, content, metadata, embedding)
                    VALUES
                        (:doc_id, :chunk_index, :content, :metadata, :embedding)
                """),
                {
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "content": chunk["content"],
                    "metadata": json.dumps(chunk["metadata"], ensure_ascii=False),
                    "embedding": format_embedding(vec),
                },
            )

        session.commit()
        logger.info("入库成功: doc_id=%d, chunks=%d", doc_id, len(chunks))
        return doc_id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def similarity_search(
    query: str,
    top_k: int = 6,
    doc_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    余弦相似度检索。

    Returns:
        [{"content", "metadata", "score"}, ...]
    """
    query_vec = embed_texts([query])[0]
    session = get_session()
    try:
        sql = """
            SELECT content, metadata,
                   1 - (embedding <=> CAST(:query_vec AS vector)) AS score
            FROM document_chunks
        """
        params: Dict[str, Any] = {"query_vec": format_embedding(query_vec), "top_k": top_k}

        if doc_type:
            sql += " WHERE metadata->>'doc_type' = :doc_type"
            params["doc_type"] = doc_type

        sql += " ORDER BY embedding <=> CAST(:query_vec AS vector) LIMIT :top_k"

        rows = session.execute(text(sql), params).fetchall()
        return [
            {
                "content": row[0],
                "metadata": json.loads(row[1]) if isinstance(row[1], str) else row[1],
                "score": float(row[2]),
            }
            for row in rows
        ]
    finally:
        session.close()


def get_all_chunks() -> List[Dict[str, Any]]:
    """获取全部 chunk，供 BM25 构建索引。"""
    session = get_session()
    try:
        rows = session.execute(
            text("SELECT id, content, metadata FROM document_chunks ORDER BY id")
        ).fetchall()
        return [
            {
                "id": row[0],
                "content": row[1],
                "metadata": json.loads(row[2]) if isinstance(row[2], str) else row[2],
            }
            for row in rows
        ]
    finally:
        session.close()


def get_stats() -> Dict[str, Any]:
    """知识库统计信息。"""
    session = get_session()
    try:
        doc_count = session.execute(text("SELECT COUNT(*) FROM documents")).scalar()
        chunk_count = session.execute(text("SELECT COUNT(*) FROM document_chunks")).scalar()
        return {"documents": doc_count, "chunks": chunk_count}
    finally:
        session.close()


def find_document_by_filename(filename: str) -> Optional[int]:
    """按文件名查找文档 ID。"""
    session = get_session()
    try:
        return session.execute(
            text("SELECT id FROM documents WHERE filename = :filename"),
            {"filename": filename},
        ).scalar()
    finally:
        session.close()


def list_documents() -> List[Dict[str, Any]]:
    """列出知识库文档及分块数量。"""
    session = get_session()
    try:
        rows = session.execute(
            text("""
                SELECT d.id, d.filename, d.doc_type, d.page_count, d.created_at,
                       COUNT(c.id) AS chunk_count
                FROM documents d
                LEFT JOIN document_chunks c ON c.doc_id = d.id
                GROUP BY d.id
                ORDER BY d.created_at DESC
            """)
        ).fetchall()
        return [
            {
                "id": row[0],
                "filename": row[1],
                "doc_type": row[2],
                "page_count": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "chunk_count": row[5],
            }
            for row in rows
        ]
    finally:
        session.close()


def delete_document(doc_id: int) -> bool:
    """删除文档及其分块（级联删除）。"""
    session = get_session()
    try:
        deleted = session.execute(
            text("DELETE FROM documents WHERE id = :doc_id RETURNING id"),
            {"doc_id": doc_id},
        ).scalar()
        session.commit()
        return deleted is not None
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_document(
    filename: str,
    doc_type: str,
    page_count: int,
    chunks: List[Dict[str, Any]],
    source: str = "",
) -> tuple[int, bool]:
    """
    按文件名去重入库：已存在则先删后插。

    Returns:
        (doc_id, is_updated)
    """
    existing_id = find_document_by_filename(filename)
    if existing_id is not None:
        delete_document(existing_id)
        doc_id = insert_document(filename, doc_type, page_count, chunks, source)
        return doc_id, True
    return insert_document(filename, doc_type, page_count, chunks, source), False
