"""从 chunks + QA 对导出 LoRA SFT 训练数据。"""
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

INSTRUCTION = SYSTEM_PROMPT


def build_sft_record(question: str, context: str, answer: str) -> Dict[str, str]:
    """构建单条 Alpaca 格式训练数据。"""
    return {
        "instruction": INSTRUCTION,
        "input": f"参考文档：\n{context}\n\n问题：{question}",
        "output": answer,
    }


def export_from_qa_pairs(
    qa_file: Path,
    output_file: Path,
    chunks_dir: Path = None,
) -> int:
    """
    从 QA 对 JSON 导出 JSONL。

    qa_file 格式：
    [
      {"question": "...", "answer": "...", "context": "..."},
      ...
    ]
    """
    with open(qa_file, "r", encoding="utf-8") as f:
        qa_pairs = json.load(f)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_file, "w", encoding="utf-8") as f:
        for qa in qa_pairs:
            record = build_sft_record(
                question=qa["question"],
                context=qa.get("context", ""),
                answer=qa["answer"],
            )
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    logger.info("导出 %d 条训练数据 → %s", count, output_file)
    return count


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="导出 LoRA SFT 数据集")
    parser.add_argument("--input", required=True, help="QA JSON 文件路径")
    parser.add_argument("--output", default="data/sft/train.jsonl", help="输出 JSONL 路径")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    export_from_qa_pairs(Path(args.input), Path(args.output))
