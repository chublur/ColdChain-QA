"""评估执行器：对比 base vs lora 模型。"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.rag.engine import RAGEngine
from src.eval.metrics import (
    semantic_score,
    temp_accuracy,
    regulation_cite_rate,
    format_compliance,
    aggregate_results,
)
from src.ingest.vector_store import get_embeddings

logger = logging.getLogger(__name__)


class EvalRunner:
    """评估 base / lora 模型表现。"""

    def __init__(self, test_cases_path: Path):
        with open(test_cases_path, "r", encoding="utf-8") as f:
            self.test_cases = json.load(f)
        self.engine = RAGEngine()
        self._embed = get_embeddings()

    def _embed_fn(self, texts: List[str]) -> List[List[float]]:
        return self._embed.embed_documents(texts)

    def run(self, model: str = "base") -> Dict[str, Any]:
        """对指定模型跑完整评估集。"""
        results = []
        for case in self.test_cases:
            start = time.perf_counter()
            try:
                resp = self.engine.ask(case["question"], model=model)
                answer = resp["answer"]
                expected = case.get("expected_answer", "")

                result = {
                    "id": case["id"],
                    "question": case["question"],
                    "category": case.get("category", ""),
                    "answer": answer,
                    "expected": expected,
                    "semantic_score": semantic_score(answer, expected, self._embed_fn),
                    "temp_accuracy": temp_accuracy(answer, expected) if case.get("check_temp") else None,
                    "regulation_cite": regulation_cite_rate(answer),
                    "format_compliance": format_compliance(answer),
                    "latency_ms": resp["latency_ms"],
                }
                results.append(result)
                logger.info(
                    "[%s] %s semantic=%.3f temp=%s",
                    model, case["id"], result["semantic_score"], result["temp_accuracy"],
                )
            except Exception as e:
                logger.error("评估失败 %s: %s", case["id"], e)
                results.append({
                    "id": case["id"],
                    "question": case["question"],
                    "error": str(e),
                    "semantic_score": 0.0,
                })

        return {"model": model, **aggregate_results(results)}

    def compare(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """对比 base vs lora。"""
        base_result = self.run(model="base")
        lora_result = self.run(model="lora")

        comparison = {
            "base": base_result,
            "lora": lora_result,
            "improvement": {
                "accuracy": round(lora_result.get("accuracy", 0) - base_result.get("accuracy", 0), 4),
                "avg_semantic": round(lora_result.get("avg_semantic", 0) - base_result.get("avg_semantic", 0), 4),
                "avg_temp_accuracy": round(
                    lora_result.get("avg_temp_accuracy", 0) - base_result.get("avg_temp_accuracy", 0), 4
                ),
                "avg_regulation_cite": round(
                    lora_result.get("avg_regulation_cite", 0) - base_result.get("avg_regulation_cite", 0), 4
                ),
            },
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(comparison, f, ensure_ascii=False, indent=2)
            logger.info("评估报告已保存: %s", output_path)

        return comparison
