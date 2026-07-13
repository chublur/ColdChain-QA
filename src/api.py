"""FastAPI 入口：REST + SSE 流式，供 Vue3 嵌入调用。"""
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional, Literal, List, Any

from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.config import settings
from src.health import get_health_status
from src.rag.engine import RAGEngine
from src.ingest.loader import ingest_file
from src.ingest.vector_store import upsert_document, list_documents, delete_document
from src.rag.retriever import invalidate_bm25_cache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

engine = RAGEngine()

SUPPORTED_SUFFIXES = ("pdf", "docx", "txt", "md")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("%s 启动完成", settings.APP_NAME)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="冷链物流智能问答 API（RAG + LoRA），支持 SSE 流式输出",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None),
) -> None:
    """支持 Header 或 Query 传参，兼容 EventSource 无法自定义 Header 的场景。"""
    token = x_api_key or api_key
    if settings.API_KEY and token != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("未捕获异常: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})


# ---------- 请求/响应模型 ----------

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    model: Literal["base", "lora"] = "base"
    doc_type: Optional[str] = None


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    model: str = "base"
    rating: Literal["good", "bad"]
    note: Optional[str] = None
    sources: List[dict] = Field(default_factory=list)


# ---------- 路由 ----------

@app.get("/health")
async def health():
    return get_health_status()


@app.post("/api/ask")
async def ask(
    req: AskRequest,
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None),
):
    """非流式问答（适合简单调用）。"""
    verify_api_key(x_api_key, api_key)
    return engine.ask(req.question, model=req.model, doc_type=req.doc_type)


@app.post("/api/ask/stream")
async def ask_stream(
    req: AskRequest,
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None),
):
    """
    SSE 流式问答（供 Vue3 嵌入页面使用）。

    事件格式：
      event: retrieval  data: {"sources": [...]}
      event: token      data: {"text": "片段"}
      event: done       data: {"latency_ms": 1234}
      event: error      data: {"message": "..."}
    """
    verify_api_key(x_api_key, api_key)

    async def event_generator():
        async for event in engine.ask_stream(req.question, model=req.model, doc_type=req.doc_type):
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"], ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())


@app.get("/api/ask/stream")
async def ask_stream_get(
    question: str = Query(..., min_length=1),
    model: Literal["base", "lora"] = "base",
    doc_type: Optional[str] = Query(None),
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None),
):
    """GET 方式 SSE（方便 EventSource 原生调用，api_key 走 query 参数）。"""
    verify_api_key(x_api_key, api_key)

    async def event_generator():
        async for event in engine.ask_stream(question, model=model, doc_type=doc_type):
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"], ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())


@app.get("/api/documents")
async def documents(
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None),
):
    """列出知识库文档。"""
    verify_api_key(x_api_key, api_key)
    return {"documents": list_documents()}


@app.delete("/api/documents/{doc_id}")
async def remove_document(
    doc_id: int,
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None),
):
    """删除指定文档及其向量分块。"""
    verify_api_key(x_api_key, api_key)
    if not delete_document(doc_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    invalidate_bm25_cache()
    return {"status": "ok", "doc_id": doc_id}


@app.post("/api/ingest")
async def ingest(
    file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None),
):
    """上传 PDF/Word/文本 文档入库（同名文件自动覆盖）。"""
    verify_api_key(x_api_key, api_key)

    suffix = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(400, f"仅支持 {', '.join(SUPPORTED_SUFFIXES)} 格式")

    upload_dir = settings.DATA_DIR / "raw"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename

    content = await file.read()
    file_path.write_bytes(content)

    try:
        result = ingest_file(file_path)
        doc_id, updated = upsert_document(
            filename=result["filename"],
            doc_type=result["doc_type"],
            page_count=result["page_count"],
            chunks=result["chunks"],
        )
        invalidate_bm25_cache()
        return {
            "doc_id": doc_id,
            "chunks": len(result["chunks"]),
            "doc_type": result["doc_type"],
            "updated": updated,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("入库失败")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/feedback")
async def feedback(
    req: FeedbackRequest,
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None),
):
    """用户反馈（供 LoRA 数据闭环）。"""
    verify_api_key(x_api_key, api_key)
    from sqlalchemy import text
    from src.ingest.vector_store import get_session

    session = get_session()
    try:
        session.execute(
            text("""
                INSERT INTO feedback (question, answer, model, rating, note, sources)
                VALUES (:question, :answer, :model, :rating, :note, :sources)
            """),
            {
                **req.model_dump(),
                "sources": json.dumps(req.sources, ensure_ascii=False),
            },
        )
        session.commit()
        return {"status": "ok"}
    finally:
        session.close()
