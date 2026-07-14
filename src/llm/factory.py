"""LLM 工厂：base / lora 模型切换，支持流式。"""
import logging
from pathlib import Path

from langchain_ollama import ChatOllama

from src.config import settings

logger = logging.getLogger(__name__)


def get_llm(model: str = "base", streaming: bool = False):
    """
    获取 LLM 实例。

    Args:
        model: "base" 使用原始模型，"lora" 使用微调后模型
        streaming: 是否启用流式输出

    若设置 USE_LOCAL_LLM=1（评估推荐）：base/lora 均走本地 transformers，对比更公平。
    否则 lora 在 Ollama 微调模型未就绪时回退本地 Peft。
    """
    import os

    use_local = os.environ.get("USE_LOCAL_LLM", "").strip().lower() in ("1", "true", "yes")
    if use_local or (model == "lora" and _should_use_local_lora()):
        from src.llm.local_peft import get_local_llm

        mode = "lora" if model == "lora" else "base"
        logger.info("使用本地 transformers 推理: mode=%s", mode)
        return get_local_llm(mode)

    model_name = settings.OLLAMA_MODEL if model == "base" else settings.OLLAMA_LORA_MODEL
    logger.debug("加载 LLM: %s (streaming=%s)", model_name, streaming)
    return ChatOllama(
        model=model_name,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=settings.TEMPERATURE,
        num_predict=settings.MAX_TOKENS,
        streaming=streaming,
    )


def _should_use_local_lora() -> bool:
    """adapter 存在且环境变量 USE_LOCAL_LORA 未显式关闭时，评估走本地 Peft。"""
    import os

    flag = os.environ.get("USE_LOCAL_LORA", "1").strip().lower()
    if flag in ("0", "false", "no"):
        return False
    adapter = Path(settings.LORA_OUTPUT_DIR)
    return (adapter / "adapter_model.safetensors").exists() or (
        adapter / "adapter_model.bin"
    ).exists()
