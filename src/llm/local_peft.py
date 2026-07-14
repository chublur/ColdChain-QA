"""本地 transformers / Peft 推理（Ollama 未导入 LoRA 时的评估兜底）。"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, Optional

from langchain_core.messages import AIMessage

from src.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cache: dict[str, Any] = {}


def clear_local_llm_cache() -> None:
    """释放本地模型显存，便于 base / lora 顺序评估。"""
    import gc

    with _lock:
        _cache.clear()
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    logger.info("已清理本地 LLM 缓存")


class _SimpleChat:
    """提供 invoke / astream，接口贴近 ChatOllama 供 RAGEngine 使用。"""

    def __init__(self, mode: str):
        self.mode = mode  # base | lora
        self.model, self.tokenizer = _load_pair(mode)

    def invoke(self, prompt: str) -> AIMessage:
        text = _generate(self.model, self.tokenizer, prompt)
        return AIMessage(content=text)

    async def astream(self, prompt: str) -> AsyncIterator[AIMessage]:
        # 评估路径主要用 invoke；流式简单整段返回
        yield AIMessage(content=_generate(self.model, self.tokenizer, prompt))


def get_local_llm(model: str = "base") -> _SimpleChat:
    return _SimpleChat(model)


def _resolve_base_path() -> Path:
    local = Path(__file__).resolve().parents[2] / ".cache" / "models" / "Qwen2.5-3B-Instruct"
    if local.exists():
        return local
    return Path(settings.LORA_BASE_MODEL)


def _resolve_lora_path() -> Path:
    """优先环境变量指定路径，再查合并权重，最后回退 adapter。"""
    import os

    override = os.environ.get("LORA_MERGED_DIR") or os.environ.get("LORA_EVAL_MODEL")
    if override:
        p = Path(override)
        if p.exists():
            return p

    merged = Path(settings.MODELS_DIR) / "merged"
    if (merged / "model.safetensors").exists() or (merged / "model.safetensors.index.json").exists():
        return merged
    return Path(settings.LORA_OUTPUT_DIR)


def _load_pair(mode: str):
    key = mode
    with _lock:
        if key in _cache:
            return _cache[key]

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if mode == "lora":
            model_path = _resolve_lora_path()
            logger.info("本地加载 LoRA/合并模型: %s", model_path)
        else:
            model_path = _resolve_base_path()
            logger.info("本地加载基座: %s", model_path)

        tokenizer = AutoTokenizer.from_pretrained(str(model_path), trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # 合并模型已是全量权重；adapter 目录才需要 Peft wrap
        is_adapter = (model_path / "adapter_config.json").exists()
        load_path = _resolve_base_path() if is_adapter else model_path

        model = AutoModelForCausalLM.from_pretrained(
            str(load_path),
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )

        if is_adapter:
            from peft import PeftModel

            logger.info("挂载 LoRA adapter: %s", model_path)
            model = PeftModel.from_pretrained(model, str(model_path))

        model.eval()
        _cache[key] = (model, tokenizer)
        return model, tokenizer


def _generate(model, tokenizer, prompt: str, max_new_tokens: Optional[int] = None) -> str:
    import torch

    max_new_tokens = max_new_tokens or settings.MAX_TOKENS
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    with torch.inference_mode():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    gen = out[0][inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(gen, skip_special_tokens=True).strip()
