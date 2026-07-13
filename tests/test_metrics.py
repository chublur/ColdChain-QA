"""冷链专属指标测试。"""
from src.eval.metrics import (
    extract_temperatures,
    temp_accuracy,
    regulation_cite_rate,
    format_compliance,
)


def test_extract_temperatures():
    temps = extract_temperatures("疫苗应在2-8°C下运输，冷冻品-18℃")
    assert len(temps) >= 2


def test_temp_accuracy_match():
    assert temp_accuracy("温控范围2-8°C", "2-8°C") == 1.0


def test_temp_accuracy_miss():
    assert temp_accuracy("常温运输即可", "2-8°C") == 0.0


def test_regulation_cite():
    assert regulation_cite_rate("依据GSP附录规定") == 1.0
    assert regulation_cite_rate("一般来说要注意温度") == 0.0


def test_format_compliance():
    answer = "【结论】应隔离\n【依据】GSP规定\n【处置建议】上报"
    assert format_compliance(answer) == 1.0


def test_aggregate_results_with_none_temp():
    from src.eval.metrics import aggregate_results

    results = [
        {"semantic_score": 0.9, "temp_accuracy": 1.0, "regulation_cite": 1.0, "format_compliance": 1.0, "latency_ms": 100},
        {"semantic_score": 0.8, "temp_accuracy": None, "regulation_cite": 0.0, "format_compliance": 0.5, "latency_ms": 200},
    ]
    summary = aggregate_results(results)
    assert summary["avg_temp_accuracy"] == 1.0
    assert summary["total"] == 2
