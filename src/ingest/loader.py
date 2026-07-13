"""PDF/Word 文档解析与分块。"""
import logging
from pathlib import Path
from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import settings

logger = logging.getLogger(__name__)

DOC_TYPE_KEYWORDS = {
    "regulation": ["规范", "标准", "GSP", "GB/T", "药典"],
    "sop": ["SOP", "操作规程", "流程", "处置"],
    "equipment": ["冷藏车", "冷库", "验证", "记录仪", "设备"],
}


def detect_doc_type(filename: str, first_page_text: str = "") -> str:
    """根据文件名和首页文本推断文档类型。"""
    combined = f"{filename} {first_page_text}"
    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return doc_type
    return "regulation"


def load_pdf(file_path: Path) -> List[Dict[str, Any]]:
    """解析 PDF，返回带页码的文本块列表。"""
    import fitz  # PyMuPDF

    doc = fitz.open(str(file_path))
    pages: List[Dict[str, Any]] = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


def load_docx(file_path: Path) -> List[Dict[str, Any]]:
    """解析 Word 文档。"""
    from docx import Document

    doc = Document(str(file_path))
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [{"page": 1, "text": full_text}] if full_text else []


def split_document(
    pages: List[Dict[str, Any]],
    filename: str,
    doc_type: str,
) -> List[Dict[str, Any]]:
    """将页面文本分块，附带 metadata。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "；", " ", ""],
    )

    chunks: List[Dict[str, Any]] = []
    for page_info in pages:
        sub_chunks = splitter.split_text(page_info["text"])
        for idx, content in enumerate(sub_chunks):
            chunks.append({
                "content": content,
                "metadata": {
                    "source": filename,
                    "page": page_info["page"],
                    "doc_type": doc_type,
                    "chunk_index": len(chunks),
                },
            })
    return chunks


def load_txt(file_path: Path) -> List[Dict[str, Any]]:
    """解析纯文本/Markdown 文档。"""
    text = file_path.read_text(encoding="utf-8").strip()
    return [{"page": 1, "text": text}] if text else []


def ingest_file(file_path: Path) -> Dict[str, Any]:
    """
    解析单个文件并分块。

    Returns:
        {"filename", "doc_type", "page_count", "chunks": [...]}
    """
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        pages = load_pdf(file_path)
    elif suffix == ".docx":
        pages = load_docx(file_path)
    elif suffix in (".txt", ".md"):
        pages = load_txt(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，仅支持 pdf/docx/txt/md")

    if not pages:
        raise ValueError(f"文件无有效文本: {file_path.name}")

    first_text = pages[0]["text"][:500]
    doc_type = detect_doc_type(file_path.name, first_text)
    chunks = split_document(pages, file_path.name, doc_type)

    logger.info(
        "解析完成: %s, type=%s, pages=%d, chunks=%d",
        file_path.name, doc_type, len(pages), len(chunks),
    )
    return {
        "filename": file_path.name,
        "doc_type": doc_type,
        "page_count": len(pages),
        "chunks": chunks,
    }
