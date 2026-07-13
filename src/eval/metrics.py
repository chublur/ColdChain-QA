"""通用评估指标。"""
import re
import logging
from typing import Dict, Any, List

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.75


def cosine_similarity(a: List[float], b: List[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if denom == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


def semantic_score(answer: str, expected: str, embed_fn) -> float:
    """语义相似度（0~1）。"""
    vecs = embed_fn([answer, expected])
    return cosine_similarity(vecs[0], vecs[1])


def extract_temperatures(text: str) -> List[str]:
    """提取文本中的温度值，如 '2-8°C'、'-18℃'。"""
    pattern = r"-?\d+(?:\.\d+)?(?:\s*[-~至]\s*-?\d+(?:\.\d+)?)?\s*[°℃]C?"
    return re.findall(pattern, text)


def temp_accuracy(answer: str, expected: str) -> float:
    """
    温度数值准确率（冷链专属）。
    1.0 = 完全匹配，0.5 = 部分匹配，0.0 = 无匹配
    """
    ans_temps = extract_temperatures(answer)
    exp_temps = extract_temperatures(expected)
    if not exp_temps:
        return 1.0
    if not ans_temps:
        return 0.0
    matched = sum(1 for t in exp_temps if any(t in a or a in t for a in ans_temps))
    return matched / len(exp_temps)


def regulation_cite_rate(answer: str) -> float:
    """法规引用率：是否引用了规范名称。"""
    keywords = ["GSP", "GB/T", "GB ", "药典", "规范", "标准"]
    return 1.0 if any(kw in answer for kw in keywords) else 0.0


def format_compliance(answer: str) -> float:
    """格式合规率：是否包含【结论】【依据】。"""
    has_conclusion = "【结论】" in answer or "结论" in answer[:20]
    has_basis = "【依据】" in answer or "依据" in answer
    return 1.0 if (has_conclusion and has_basis) else 0.5 if has_conclusion else 0.0


def _safe_avg(values: List[Any]) -> float:
    """忽略 None 后求平均，避免 check_temp=false 时汇总崩溃。"""
    nums = [v for v in values if v is not None]
    return round(sum(nums) / len(nums), 4) if nums else 0.0


def aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """汇总评估结果。"""
    if not results:
        return {}
    n = len(results)
    return {
        "total": n,
        "accuracy": round(sum(1 for r in results if r["semantic_score"] >= DEFAULT_THRESHOLD) / n, 4),
        "avg_semantic": round(sum(r["semantic_score"] for r in results) / n, 4),
        "avg_faithfulness": _safe_avg([r.get("faithfulness") for r in results]),
        "avg_temp_accuracy": _safe_avg([r.get("temp_accuracy") for r in results]),
        "avg_regulation_cite": round(sum(r.get("regulation_cite", 0) for r in results) / n, 4),
        "avg_format": round(sum(r.get("format_compliance", 0) for r in results) / n, 4),
        "avg_latency_ms": round(sum(r.get("latency_ms", 0) for r in results) / n),
        "details": results,
    }
