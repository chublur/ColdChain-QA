"""评估 CLI：对比 base vs lora 模型。"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.eval.runner import EvalRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="冷链 QA 模型评估")
    parser.add_argument("--model", choices=["base", "lora", "compare"], default="compare")
    parser.add_argument("--test", default=str(settings.DATA_DIR / "sft" / "test_cases.json"))
    parser.add_argument("--output", default=str(settings.CACHE_DIR / "eval_report.json"))
    args = parser.parse_args()

    runner = EvalRunner(Path(args.test))

    if args.model == "compare":
        result = runner.compare(output_path=Path(args.output))
        imp = result["improvement"]
        print("\n===== base vs lora 对比 =====")
        print(f"准确率提升:     {imp['accuracy']:+.2%}")
        print(f"语义相似度提升: {imp['avg_semantic']:+.4f}")
        print(f"温度准确率提升: {imp['avg_temp_accuracy']:+.4f}")
        print(f"法规引用率提升: {imp['avg_regulation_cite']:+.4f}")
        print(f"报告已保存: {args.output}")
    else:
        result = runner.run(model=args.model)
        print(f"\n===== {args.model} 评估结果 =====")
        for k, v in result.items():
            if k != "details":
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
