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
        # 本地 transformers 推理时需释放显存再加载 lora
        try:
            from src.llm.local_peft import clear_local_llm_cache

            clear_local_llm_cache()
        except Exception:
            pass
        lora_result = self.run(model="lora")

        metric_keys = [
            "accuracy",
            "avg_semantic",
            "avg_faithfulness",
            "avg_temp_accuracy",
            "avg_regulation_cite",
            "avg_format",
            "avg_latency_ms",
        ]
        improvement = {}
        for key in metric_keys:
            base_v = base_result.get(key, 0) or 0
            lora_v = lora_result.get(key, 0) or 0
            # 延迟：负向指标，提升用 base - lora（越小越好）
            if key == "avg_latency_ms":
                improvement[key] = round(base_v - lora_v, 4)
            else:
                improvement[key] = round(lora_v - base_v, 4)

        comparison = {
            "base": base_result,
            "lora": lora_result,
            "improvement": improvement,
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(comparison, f, ensure_ascii=False, indent=2)
            logger.info("评估报告已保存: %s", output_path)

        return comparison
