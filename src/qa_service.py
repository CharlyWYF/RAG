from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from src.config import load_settings
from src.qa import PROMPT_TEMPLATE, _join_context, build_llm
from src.retriever import get_retriever

QUERY_REWRITE_PROMPT = """你是检索查询优化助手。请根据用户问题生成 2 条彼此互补、适合网络协议知识库检索的子查询。

要求：
1. 保留协议名、字段名、机制名等关键术语。
2. 每条子查询聚焦不同角度，例如定义 / 流程 / 对比 / 字段。
3. 不要回答问题，只改写为适合向量检索的短查询。
4. 去口语化，但不要扩写成多句解释。
5. 只输出 2 行，每行 1 条子查询，不要加编号，不要解释。

用户问题：
{question}
"""


class AnswerStreamHandler:
    def on_setup(self, question: str) -> None:
        pass

    def on_chunk(self, text: str) -> None:
        pass

    def on_first_token(self, seconds: float) -> None:
        pass

    def on_complete(self, answer: str) -> None:
        pass


def execute_qa_flow(
    question: str,
    progress_callback: Callable[[str], None] | None = None,
    stream_handler: AnswerStreamHandler | None = None,
) -> dict[str, Any]:
    def report(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    q = question.strip()
    timings: list[dict[str, Any]] = []
    t0 = perf_counter()

    report("开始加载配置...")
    t1_start = perf_counter()
    settings = load_settings()
    t1_end = perf_counter()
    timings.append({"stage": "load_settings", "seconds": t1_end - t1_start})

    report("正在查询改写...")
    t_rewrite_start = perf_counter()
    rewrite_llm = build_llm(settings, model_override=settings.query_rewrite_model)
    rewritten_raw = rewrite_llm.invoke(QUERY_REWRITE_PROMPT.format(question=q)).content.strip()
    rewritten_queries = list(dict.fromkeys(
        line.strip()
        for line in rewritten_raw.splitlines()
        if line.strip()
    ))[:2]
    t_rewrite_end = perf_counter()
    timings.append({"stage": "rewrite_query", "seconds": t_rewrite_end - t_rewrite_start})

    report("正在初始化检索器...")
    t2_start = perf_counter()
    retriever = get_retriever()
    t2_end = perf_counter()
    timings.append({"stage": "init_retriever", "seconds": t2_end - t2_start})

    report("正在执行向量检索...")
    t3_start = perf_counter()
    retrieval_queries = [q, *rewritten_queries]
    merged_docs: list[Any] = []
    seen_chunks: set[tuple[str, str]] = set()
    for retrieval_query in retrieval_queries:
        query_docs = retriever.invoke(retrieval_query)
        for doc in query_docs:
            source = str(getattr(doc, "metadata", {}).get("source", "unknown"))
            content = str(getattr(doc, "page_content", ""))
            chunk_key = (source, content)
            if chunk_key in seen_chunks:
                continue
            seen_chunks.add(chunk_key)
            merged_docs.append(doc)
    docs = merged_docs
    t3_end = perf_counter()
    timings.append({"stage": "retrieve", "seconds": t3_end - t3_start})

    context = _join_context(docs)
    if not context.strip():
        total_seconds = perf_counter() - t0
        timings.append({"stage": "total", "seconds": total_seconds})
        return {
            "answer": "资料不足以确定，请先补充相关协议文档。",
            "contexts": [],
            "sources": [],
            "rewritten_queries": rewritten_queries,
            "timings": timings,
            "total_seconds": total_seconds,
            "logs": [
                "load_settings",
                "rewrite_query",
                "init_retriever",
                "retrieve",
                "no_context",
            ],
        }

    report("正在初始化大模型客户端...")
    t4_start = perf_counter()
    llm = build_llm(settings)
    t4_end = perf_counter()
    timings.append({"stage": "init_llm", "seconds": t4_end - t4_start})

    if stream_handler:
        stream_handler.on_setup(q)

    prompt = PROMPT_TEMPLATE.format(question=q, context=context)
    report("正在生成最终回答...")
    t5_start = perf_counter()
    first_token_seconds: float | None = None
    chunks: list[str] = []
    for chunk in llm.stream(prompt):
        chunk_text = getattr(chunk, "content", "")
        if isinstance(chunk_text, list):
            chunk_text = "".join(str(part) for part in chunk_text)
        if not chunk_text:
            continue
        if first_token_seconds is None:
            first_token_seconds = perf_counter() - t0
            if stream_handler:
                stream_handler.on_first_token(first_token_seconds)
        text = str(chunk_text)
        chunks.append(text)
        if stream_handler:
            stream_handler.on_chunk(text)
    t5_end = perf_counter()

    if first_token_seconds is not None:
        timings.append({"stage": "first_token", "seconds": first_token_seconds})
        timings.append({
            "stage": "generate_first_token",
            "seconds": first_token_seconds - sum(
                float(item.get("seconds", 0.0))
                for item in timings
                if str(item.get("stage", "")) in {
                    "load_settings",
                    "rewrite_query",
                    "init_retriever",
                    "retrieve",
                    "init_llm",
                }
            ),
        })
    timings.append({"stage": "generate_answer", "seconds": t5_end - t5_start})

    total_seconds = perf_counter() - t0
    timings.append({"stage": "total", "seconds": total_seconds})

    answer = "".join(chunks)
    if stream_handler:
        stream_handler.on_complete(answer)

    return {
        "answer": answer,
        "contexts": [doc.page_content for doc in docs],
        "sources": [str(doc.metadata.get("source", "unknown")) for doc in docs],
        "rewritten_queries": rewritten_queries,
        "timings": timings,
        "total_seconds": total_seconds,
        "logs": [
            "load_settings",
            "rewrite_query",
            "init_retriever",
            "retrieve",
            "init_llm",
            "first_token" if first_token_seconds is not None else "no_first_token",
            "generate_answer",
            "done",
        ],
    }
