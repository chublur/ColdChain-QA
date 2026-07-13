"""混合检索：pgvector 向量 + BM25 关键词。"""
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional

from rank_bm25 import BM25Okapi

from src.config import settings
from src.ingest.vector_store import similarity_search, get_all_chunks

logger = logging.getLogger(__name__)

_bm25_index: Optional[BM25Okapi] = None
_bm25_chunks: List[Dict[str, Any]] = []
_BM25_CACHE = Path(settings.CACHE_DIR) / "bm25_index.pkl"


def _tokenize(text: str) -> List[str]:
    """简单中文分词：按字切分 + 保留英文单词。"""
    import re
    tokens = []
    for segment in re.split(r"([\u4e00-\u9fff])", text):
        segment = segment.strip()
        if not segment:
            continue
        if re.match(r"[\u4e00-\u9fff]", segment):
            tokens.append(segment)
        else:
            tokens.extend(w for w in segment.split() if w)
    return tokens


def _build_bm25() -> None:
    """从数据库构建 BM25 索引。"""
    global _bm25_index, _bm25_chunks

    if _BM25_CACHE.exists():
        with open(_BM25_CACHE, "rb") as f:
            data = pickle.load(f)
            _bm25_chunks = data["chunks"]
            _bm25_index = data["index"]
        logger.info("BM25 索引从缓存加载: %d chunks", len(_bm25_chunks))
        return

    _bm25_chunks = get_all_chunks()
    if not _bm25_chunks:
        logger.warning("无 chunk 数据，BM25 索引为空")
        return

    corpus = [_tokenize(c["content"]) for c in _bm25_chunks]
    _bm25_index = BM25Okapi(corpus)

    _BM25_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(_BM25_CACHE, "wb") as f:
        pickle.dump({"chunks": _bm25_chunks, "index": _bm25_index}, f)
    logger.info("BM25 索引已构建: %d chunks", len(_bm25_chunks))


def bm25_search(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """BM25 关键词检索。"""
    if _bm25_index is None:
        _build_bm25()
    if not _bm25_index or not _bm25_chunks:
        return []

    tokens = _tokenize(query)
    scores = _bm25_index.get_scores(tokens)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]

    results = []
    for idx, score in ranked:
        if score <= 0:
            continue
        chunk = _bm25_chunks[idx]
        results.append({
            "content": chunk["content"],
            "metadata": chunk["metadata"],
            "score": float(score),
            "source": "bm25",
        })
    return results


def hybrid_search(
    query: str,
    top_k: int = None,
    doc_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    混合检索：向量 60% + BM25 40% 权重融合。

    Returns:
        去重后的 top_k 结果
    """
    top_k = top_k or settings.RETRIEVAL_TOP_K
    vector_results = similarity_search(query, top_k=top_k, doc_type=doc_type)

    for r in vector_results:
        r["source"] = "vector"

    if not settings.BM25_ENABLED:
        return vector_results[:top_k]

    bm25_results = bm25_search(query, top_k=top_k // 2 + 2)

    # 归一化分数后融合
    merged: Dict[str, Dict[str, Any]] = {}

    if vector_results:
        max_v = max(r["score"] for r in vector_results) or 1.0
        for r in vector_results:
            key = r["content"][:80]
            merged[key] = {**r, "final_score": r["score"] / max_v * 0.6}

    if bm25_results:
        max_b = max(r["score"] for r in bm25_results) or 1.0
        for r in bm25_results:
            key = r["content"][:80]
            norm = r["score"] / max_b * 0.4
            if key in merged:
                merged[key]["final_score"] += norm
            else:
                merged[key] = {**r, "final_score": norm}

    ranked = sorted(merged.values(), key=lambda x: x["final_score"], reverse=True)
    return ranked[:top_k]


def invalidate_bm25_cache() -> None:
    """新文档入库后清除 BM25 缓存。"""
    global _bm25_index, _bm25_chunks
    _bm25_index = None
    _bm25_chunks = []
    if _BM25_CACHE.exists():
        _BM25_CACHE.unlink()
    logger.info("BM25 缓存已清除")
