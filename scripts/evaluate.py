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
        _print_compare_report(result)
        print(f"\n报告已保存: {args.output}")
    else:
        result = runner.run(model=args.model)
        _print_single_report(args.model, result)


def _print_single_report(model: str, result: dict) -> None:
    print(f"\n===== {model} 评估结果 =====")
    labels = {
        "total": "样本数",
        "accuracy": "准确率 (semantic≥0.75)",
        "avg_semantic": "平均语义相似度",
        "avg_faithfulness": "平均忠实度",
        "avg_temp_accuracy": "平均温度准确率",
        "avg_regulation_cite": "平均法规引用率",
        "avg_format": "平均格式合规率",
        "avg_latency_ms": "平均延迟(ms)",
    }
    for k, label in labels.items():
        if k not in result:
            continue
        v = result[k]
        if k == "accuracy":
            print(f"  {label}: {v:.2%}")
        elif k == "avg_latency_ms":
            print(f"  {label}: {v}")
        else:
            print(f"  {label}: {v:.4f}")


def _print_compare_report(result: dict) -> None:
    """打印 base / lora 各指标对照及提升幅度。"""
    base = result["base"]
    lora = result["lora"]
    imp = result["improvement"]

    rows = [
        ("准确率 (semantic≥0.75)", "accuracy", True, False),
        ("平均语义相似度", "avg_semantic", False, False),
        ("平均忠实度", "avg_faithfulness", False, False),
        ("平均温度准确率", "avg_temp_accuracy", False, False),
        ("平均法规引用率", "avg_regulation_cite", False, False),
        ("平均格式合规率", "avg_format", False, False),
        ("平均延迟(ms)", "avg_latency_ms", False, True),
    ]

    print("\n===== base vs lora 指标对比 =====")
    print(f"{'指标':<22} {'base':>10} {'lora':>10} {'提升':>12}")
    print("-" * 58)
    for label, key, is_pct, lower_better in rows:
        b = base.get(key, 0) or 0
        l = lora.get(key, 0) or 0
        d = imp.get(key, 0) or 0
        if is_pct:
            print(f"{label:<22} {b:>9.2%} {l:>9.2%} {d:>+11.2%}")
        elif lower_better:
            # 延迟：improvement 已是 base-lora，正数表示变快
            print(f"{label:<22} {b:>10.0f} {l:>10.0f} {d:>+10.0f}ms")
        else:
            print(f"{label:<22} {b:>10.4f} {l:>10.4f} {d:>+11.4f}")

    print("-" * 58)
    print("说明: 除延迟外，提升 = lora - base（正数越好）；延迟提升 = base - lora（正数表示更快）")


if __name__ == "__main__":
    main()
