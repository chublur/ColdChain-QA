"""批量将 data/raw/ 下文档入库（同名文件自动覆盖）。"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.ingest.loader import ingest_file
from src.ingest.vector_store import upsert_document
from src.rag.retriever import invalidate_bm25_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORTED_GLOBS = ("*.pdf", "*.docx", "*.txt", "*.md")


def main():
    raw_dir = settings.DATA_DIR / "raw"
    files: list[Path] = []
    for pattern in SUPPORTED_GLOBS:
        files.extend(raw_dir.glob(pattern))

    if not files:
        logger.warning("data/raw/ 下无文档，请先放入冷链 PDF/Word/文本")
        return

    total_chunks = 0
    updated_count = 0
    for file_path in sorted(files):
        try:
            result = ingest_file(file_path)
            doc_id, updated = upsert_document(
                filename=result["filename"],
                doc_type=result["doc_type"],
                page_count=result["page_count"],
                chunks=result["chunks"],
            )
            total_chunks += len(result["chunks"])
            if updated:
                updated_count += 1
            action = "更新" if updated else "新增"
            logger.info("✓ %s %s → doc_id=%d, chunks=%d", action, file_path.name, doc_id, len(result["chunks"]))
        except Exception as e:
            logger.error("✗ %s 失败: %s", file_path.name, e)

    invalidate_bm25_cache()
    logger.info(
        "入库完成，共 %d 个文件（更新 %d 个），%d 个 chunk",
        len(files), updated_count, total_chunks,
    )


if __name__ == "__main__":
    main()
