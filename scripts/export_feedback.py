"""将 feedback 表中 good 评价导出为 SFT 训练数据。"""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from src.config import settings
from src.ingest.vector_store import get_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_good_feedback() -> list[dict]:
    session = get_session()
    try:
        rows = session.execute(
            text("""
                SELECT question, answer
                FROM feedback
                WHERE rating = 'good' AND answer IS NOT NULL
                ORDER BY created_at
            """)
        ).fetchall()
        return [{"question": r[0], "answer": r[1]} for r in rows]
    finally:
        session.close()


def merge_qa_pairs(existing: list[dict], feedback_items: list[dict]) -> list[dict]:
    """按 question 去重合并，feedback 优先覆盖。"""
    merged = {item["question"]: item for item in existing}
    for item in feedback_items:
        merged[item["question"]] = item
    return list(merged.values())


def main():
    parser = argparse.ArgumentParser(description="导出 good 反馈为 SFT 数据")
    parser.add_argument(
        "--output",
        default=str(settings.DATA_DIR / "sft" / "qa_pairs.json"),
        help="输出路径",
    )
    parser.add_argument(
        "--merge-existing",
        action="store_true",
        help="与已有 qa_pairs.json 合并去重",
    )
    args = parser.parse_args()

    feedback_items = fetch_good_feedback()
    if not feedback_items:
        logger.warning("无 good 反馈可导出")
        return

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.merge_existing and output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        result = merge_qa_pairs(existing, feedback_items)
    else:
        result = feedback_items

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info("已导出 %d 条 QA 到 %s", len(result), output_path)


if __name__ == "__main__":
    main()
