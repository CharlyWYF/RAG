from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src.config import load_settings
from src.retriever import get_retriever

PROMPT_TEMPLATE = """你是一个网络协议学习助手。请严格依据给定上下文回答问题。

规则：
1) 如果上下文足以回答，先给简明结论，再给关键细节。
2) 如果上下文不足，请明确说“资料不足以确定”，不要编造。
3) 回答尽量结构化、易懂。

问题：
{question}

上下文：
{context}
"""


def _join_context(docs: list[Any]) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def build_llm(settings):
    llm_kwargs = {
        "model": settings.chat_model,
        "api_key": settings.openai_api_key,
    }
    if settings.openai_base_url:
        llm_kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**llm_kwargs)


def _build_embeddings(settings):
    embedding_kwargs = {
        "model": settings.embedding_model,
        "api_key": settings.openai_api_key,
    }
    if settings.openai_base_url:
        embedding_kwargs["base_url"] = settings.openai_base_url
    return OpenAIEmbeddings(**embedding_kwargs)


def health_check() -> dict[str, str]:
    settings = load_settings()

    _build_llm(settings).invoke("请只回复: OK")
    _build_embeddings(settings).embed_query("network protocol health check")

    return {
        "status": "ok",
        "chat_model": settings.chat_model,
        "embedding_model": settings.embedding_model,
        "base_url": settings.openai_base_url or "(default)",
    }


def answer_question(
    question: str,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    def report(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    timings: list[dict[str, Any]] = []

    t0 = perf_counter()
    report("开始加载配置...")
    settings = load_settings()
    t1 = perf_counter()
    timings.append({"stage": "load_settings", "seconds": t1 - t0})

    report("正在初始化检索器...")
    t2_start = perf_counter()
    retriever = get_retriever()
    t2_end = perf_counter()
    timings.append({"stage": "init_retriever", "seconds": t2_end - t2_start})

    report("正在执行向量检索...")
    t3_start = perf_counter()
    docs = retriever.invoke(question)
    t3_end = perf_counter()
    timings.append({"stage": "retrieve", "seconds": t3_end - t3_start})

    context = _join_context(docs)
    if not context.strip():
        total_seconds = perf_counter() - t0
        timings.append({"stage": "total", "seconds": total_seconds})
        report("检索完成：未找到可用上下文。")
        return {
            "answer": "资料不足以确定，请先补充相关协议文档。",
            "contexts": [],
            "sources": [],
            "timings": timings,
            "total_seconds": total_seconds,
            "logs": [
                "load_settings",
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

    report("正在生成最终回答...")
    prompt = PROMPT_TEMPLATE.format(question=question, context=context)
    t5_start = perf_counter()
    first_token_seconds: float | None = None
    chunks: list[str] = []
    for chunk in llm.stream(prompt):
        chunk_text = getattr(chunk, "content", "")
        if isinstance(chunk_text, list):
            chunk_text = "".join(str(part) for part in chunk_text)
        if chunk_text:
            if first_token_seconds is None:
                first_token_seconds = perf_counter() - t5_start
            chunks.append(str(chunk_text))
    t5_end = perf_counter()
    if first_token_seconds is not None:
        timings.append({"stage": "first_token", "seconds": first_token_seconds})
    timings.append({"stage": "generate_answer", "seconds": t5_end - t5_start})

    total_seconds = perf_counter() - t0
    timings.append({"stage": "total", "seconds": total_seconds})

    contexts = [doc.page_content for doc in docs]
    sources = [str(doc.metadata.get("source", "unknown")) for doc in docs]

    report("问答完成。")
    return {
        "answer": "".join(chunks),
        "contexts": contexts,
        "sources": sources,
        "timings": timings,
        "total_seconds": total_seconds,
        "logs": [
            "load_settings",
            "init_retriever",
            "retrieve",
            "init_llm",
            "first_token" if first_token_seconds is not None else "no_first_token",
            "generate_answer",
            "done",
        ],
    }
