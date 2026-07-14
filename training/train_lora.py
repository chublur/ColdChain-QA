"""
QLoRA 微调脚本（RTX 4060 8GB 轻量化配置）。

用法：
  python training/train_lora.py

训练完成后：
  1. adapter 保存在 models/lora_adapter/
  2. 按 docs/DEVELOPMENT_FLOW.md 合并并导入 Ollama
"""
import logging
import os
import sys
from pathlib import Path

# 将项目根目录加入 path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 缓存/临时文件一律落在项目盘（E:），避免占满 C:
_cache = ROOT / ".cache"
for _name, _sub in [
    ("HF_HOME", "huggingface"),
    ("HUGGINGFACE_HUB_CACHE", "huggingface/hub"),
    ("TRANSFORMERS_CACHE", "huggingface/transformers"),
    ("TORCH_HOME", "torch"),
    ("TMPDIR", "tmp"),
    ("TEMP", "tmp"),
    ("TMP", "tmp"),
]:
    _path = _cache / _sub
    _path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(_name, str(_path))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def train():
    from datasets import load_dataset
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTConfig, SFTTrainer
    from src.config import settings

    train_file = settings.DATA_DIR / "sft" / "train.jsonl"
    if not train_file.exists():
        raise FileNotFoundError(
            f"训练数据不存在: {train_file}\n"
            "请先运行: python training/export_dataset.py --input data/sft/qa_pairs.json"
        )

    logger.info("加载数据集: %s", train_file)
    dataset = load_dataset("json", data_files=str(train_file), split="train")

    def format_sample(sample):
        return (
            f"<|im_start|>system\n{sample['instruction']}\n"
            f"<|im_start|>user\n{sample['input']}\n"
            f"<|im_start|>assistant\n{sample['output']}"
        )

    logger.info("加载基座模型: %s", settings.LORA_BASE_MODEL)

    # RTX 4060：统一 float16，避免 GradScaler 与 bf16 梯度冲突
    compute_dtype = torch.float16

    bnb_config = None
    if settings.LORA_4BIT:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
        )

    tokenizer = AutoTokenizer.from_pretrained(settings.LORA_BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        settings.LORA_BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=compute_dtype,
    )
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=settings.LORA_R,
        lora_alpha=settings.LORA_ALPHA,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    output_dir = str(settings.LORA_OUTPUT_DIR)
    # trl>=0.12：max_length 等放在 SFTConfig（兼容 TrainingArguments 字段）
    training_args = SFTConfig(
        output_dir=output_dir,
        num_train_epochs=settings.LORA_EPOCHS,
        per_device_train_batch_size=settings.LORA_BATCH_SIZE,
        gradient_accumulation_steps=settings.LORA_GRAD_ACCUM,
        learning_rate=2e-4,
        # 关闭混合精度：当前 torch/accelerate 在 GradScaler+半精度梯度上会报 BFloat16 unscale 错误
        fp16=False,
        bf16=False,
        logging_steps=10,
        save_strategy="epoch",
        optim="paged_adamw_8bit",
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        report_to="none",
        max_grad_norm=0.0,
        max_length=settings.LORA_MAX_SEQ_LEN,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
        formatting_func=format_sample,
    )

    logger.info("开始 QLoRA 训练 (r=%d, epochs=%d, batch=%d×%d)",
                settings.LORA_R, settings.LORA_EPOCHS,
                settings.LORA_BATCH_SIZE, settings.LORA_GRAD_ACCUM)
    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info("训练完成，adapter 已保存: %s", output_dir)


if __name__ == "__main__":
    train()
