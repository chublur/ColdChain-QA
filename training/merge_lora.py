"""
合并 LoRA adapter 到基座，输出到 models/merged/（落在项目盘）。

用法：
  .venv\\Scripts\\python.exe training/merge_lora.py
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_cache = ROOT / ".cache"
for _name, _sub in [
    ("HF_HOME", "huggingface"),
    ("TRANSFORMERS_CACHE", "huggingface/transformers"),
    ("TORCH_HOME", "torch"),
    ("TEMP", "tmp"),
    ("TMP", "tmp"),
]:
    _path = _cache / _sub
    _path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(_name, str(_path))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def merge():
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from src.config import settings

    base_path = Path(os.environ.get("LORA_BASE_MODEL", settings.LORA_BASE_MODEL))
    # 优先本地 ModelScope 副本，避免再次联网
    local_base = ROOT / ".cache" / "models" / "Qwen2.5-3B-Instruct"
    if local_base.exists():
        base_path = local_base

    adapter_dir = Path(os.environ.get("LORA_OUTPUT_DIR", settings.LORA_OUTPUT_DIR))
    if not (adapter_dir / "adapter_model.safetensors").exists() and not (
        adapter_dir / "adapter_model.bin"
    ).exists():
        raise FileNotFoundError(f"未找到 adapter: {adapter_dir}")

    out_dir = Path(os.environ.get("MERGED_OUTPUT_DIR", settings.MODELS_DIR / "merged"))
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("基座: %s", base_path)
    logger.info("adapter: %s", adapter_dir)
    logger.info("输出: %s", out_dir)

    tokenizer = AutoTokenizer.from_pretrained(str(base_path), trust_remote_code=True)
    # 合并阶段用 CPU/半精度，省显存；合并完即可卸载
    model = AutoModelForCausalLM.from_pretrained(
        str(base_path),
        torch_dtype=torch.float16,
        device_map="cpu",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(model, str(adapter_dir))
    model = model.merge_and_unload()

    model.save_pretrained(str(out_dir), safe_serialization=True)
    tokenizer.save_pretrained(str(out_dir))
    logger.info("合并完成 → %s", out_dir)
    return out_dir


if __name__ == "__main__":
    merge()
