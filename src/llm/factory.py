"""LLM 工厂：base / lora 模型切换，支持流式。"""
import logging

from langchain_ollama import ChatOllama

from src.config import settings

logger = logging.getLogger(__name__)


def get_llm(model: str = "base", streaming: bool = False) -> ChatOllama:
    """
    获取 LLM 实例。

    Args:
        model: "base" 使用原始模型，"lora" 使用微调后模型
        streaming: 是否启用流式输出
    """
    model_name = settings.OLLAMA_MODEL if model == "base" else settings.OLLAMA_LORA_MODEL
    logger.debug("加载 LLM: %s (streaming=%s)", model_name, streaming)
    return ChatOllama(
        model=model_name,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=settings.TEMPERATURE,
        num_predict=settings.MAX_TOKENS,
        streaming=streaming,
    )
