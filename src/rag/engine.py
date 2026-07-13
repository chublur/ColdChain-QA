"""RAG 问答引擎（支持流式 / 非流式）。"""

import logging
import time
from typing import Dict, Any, List, AsyncIterator, Optional

from src.rag.retriever import hybrid_search
from src.rag.prompt import build_rag_prompt, format_context
from src.llm.factory import get_llm

logger = logging.getLogger(__name__)


class RAGEngine:
    """冷链 RAG 引擎。"""

    def retrieve(
        self, question: str, doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return hybrid_search(question, doc_type=doc_type)

    def build_prompt(self, question: str, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return build_rag_prompt(question, "（未检索到相关文档）")
        return build_rag_prompt(question, format_context(chunks))

    def ask(
        self,
        question: str,
        model: str = "base",
        doc_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """非流式问答，返回完整结果。"""
        start = time.perf_counter()
        chunks = self.retrieve(question, doc_type=doc_type)
        prompt = self.build_prompt(question, chunks)

        llm = get_llm(model=model)
        answer = llm.invoke(prompt)

        return {
            "question": question,
            "answer": answer.content if hasattr(answer, "content") else str(answer),
            "sources": [
                {
                    "content": c["content"][:200],
                    "source": c.get("metadata", {}).get("source", ""),
                    "page": c.get("metadata", {}).get("page", ""),
                    "score": round(c.get("final_score", c.get("score", 0)), 4),
                }
                for c in chunks
            ],
            "model": model,
            "latency_ms": round((time.perf_counter() - start) * 1000),
        }

    async def ask_stream(
        self,
        question: str,
        model: str = "base",
        doc_type: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式问答，yield SSE 事件数据。

        事件类型：
          - retrieval: 检索完成，附带 sources
          - token: 生成的文本片段
          - done: 完成，附带 latency_ms
          - error: 错误信息
        """
        start = time.perf_counter()
        try:
            chunks = self.retrieve(question, doc_type=doc_type)
            sources = [
                {
                    "content": c["content"][:200],
                    "source": c.get("metadata", {}).get("source", ""),
                    "page": c.get("metadata", {}).get("page", ""),
                    "score": round(c.get("final_score", c.get("score", 0)), 4),
                }
                for c in chunks
            ]
            yield {"event": "retrieval", "data": {"sources": sources}}

            prompt = self.build_prompt(question, chunks)
            llm = get_llm(model=model, streaming=True)

            async for chunk in llm.astream(prompt):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)
                if token:
                    yield {"event": "token", "data": {"text": token}}

            yield {
                "event": "done",
                "data": {"latency_ms": round((time.perf_counter() - start) * 1000)},
            }
        except Exception as e:
            logger.exception("流式问答异常")
            yield {"event": "error", "data": {"message": str(e)}}
