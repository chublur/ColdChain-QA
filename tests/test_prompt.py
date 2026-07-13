"""Prompt 模板测试。"""
from src.rag.prompt import build_rag_prompt, format_context


def test_build_rag_prompt():
    prompt = build_rag_prompt("疫苗运输温度？", "参考文档内容")
    assert "冷链物流合规顾问" in prompt
    assert "疫苗运输温度" in prompt
    assert "【结论】" in prompt


def test_format_context():
    chunks = [
        {"content": "温度2-8°C", "metadata": {"source": "GSP.pdf", "page": 3}},
    ]
    ctx = format_context(chunks)
    assert "GSP.pdf" in ctx
    assert "2-8°C" in ctx
