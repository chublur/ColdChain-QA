"""依赖服务健康检查。"""

import logging
from typing import Any, Dict

import httpx
from sqlalchemy import text

from src.config import settings
from src.ingest.vector_store import get_session, get_stats

logger = logging.getLogger(__name__)


def check_postgres() -> Dict[str, Any]:
    """检查 PostgreSQL 连接。"""
    try:
        session = get_session()
        session.execute(text("SELECT 1"))
        session.close()
        return {"status": "ok"}
    except Exception as e:
        logger.warning("PostgreSQL 不可用: %s", e)
        return {"status": "error", "message": str(e)}


def check_ollama() -> Dict[str, Any]:
    """检查 Ollama 服务及模型就绪状态。"""
    import os

    # 本地 transformers 推理时不阻塞等 Ollama（常导致前端健康检查 pending）
    if os.environ.get("USE_LOCAL_LLM", "").strip().lower() in ("1", "true", "yes"):
        return {
            "status": "skipped",
            "message": "USE_LOCAL_LLM=1，跳过 Ollama 检查",
            "base_ready": True,
            "lora_ready": True,
        }

    try:
        with httpx.Client(timeout=1.5) as client:
            resp = client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            base_ready = any(settings.OLLAMA_MODEL in m for m in models)
            lora_ready = any(settings.OLLAMA_LORA_MODEL in m for m in models)
            return {
                "status": "ok",
                "base_ready": base_ready,
                "lora_ready": lora_ready,
                "models": models,
            }
    except Exception as e:
        logger.warning("Ollama 不可用: %s", e)
        return {"status": "error", "message": str(e)}


def get_health_status() -> Dict[str, Any]:
    """汇总后端依赖健康状态。"""
    import os

    postgres = check_postgres()
    ollama = check_ollama()
    kb = get_stats() if postgres["status"] == "ok" else {"documents": 0, "chunks": 0}

    use_local = os.environ.get("USE_LOCAL_LLM", "").strip().lower() in ("1", "true", "yes")
    llm_ok = use_local or ollama["status"] == "ok"
    services_ok = postgres["status"] == "ok" and llm_ok
    kb_ready = kb.get("chunks", 0) > 0

    return {
        "status": "ok" if services_ok and kb_ready else "degraded",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "kb": kb,
        "postgres": postgres,
        "ollama": ollama,
    }
