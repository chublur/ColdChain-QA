"""冷链领域专用 Prompt 模板。"""

SYSTEM_PROMPT = """你是冷链物流合规顾问，专注于医药/食品冷链运输与仓储合规问答。

回答要求：
1. 温度数据必须准确，不得猜测或编造
2. 优先引用文档中的规范名称和条款
3. 严格使用以下格式：
   【结论】一句话直接回答
   【依据】引用文档中的相关规定
   【处置建议】具体操作步骤（如适用）
4. 若文档未提及，明确回答「文档中未找到相关规定，建议查阅最新版 GSP/国标或咨询质量负责人」
5. 不要编造法规编号、温度范围、处置流程"""

RAG_TEMPLATE = """{system_prompt}

参考文档：
{context}

用户问题：{question}

请按格式回答："""


def build_rag_prompt(question: str, context: str) -> str:
    """构建完整 RAG Prompt。"""
    return RAG_TEMPLATE.format(
        system_prompt=SYSTEM_PROMPT,
        context=context,
        question=question,
    )


def format_context(chunks: list) -> str:
    """将检索结果格式化为上下文文本。"""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "未知")
        page = meta.get("page", "?")
        parts.append(f"[{i}] 来源: {source} 第{page}页\n{chunk['content']}")
    return "\n\n".join(parts)
