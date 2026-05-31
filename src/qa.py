"""RAG 问答模块：检索增强生成 + 流式输出。"""
from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src.config import load_settings
from src.retriever import get_retriever

# v1 为早期简洁版 prompt
PROMPT_TEMPLATE_V1 = """你是一个网络协议学习助手。请严格依据给定上下文回答问题。

规则：
1) 如果上下文足以回答，先给简明结论，再给关键细节。
2) 如果上下文不足，请明确说"资料不足以确定"，不要编造。
3) 回答尽量结构化、易懂。

问题：
{question}

上下文：
{context}
"""

# v2 增加了对比类、流程类、字段类问题的结构化指引，抑制幻觉效果更好
PROMPT_TEMPLATE_V2 = """你是一个网络协议学习助手。请严格依据给定上下文回答问题，不要使用上下文之外的常识补全结论。

规则：
1) 如果上下文足以回答，先给简明结论，再给关键细节。
2) 如果上下文不足，请明确说"资料不足以确定"，不要编造，不要扩展推断。
3) 回答尽量结构化、易懂。
4) 如果问题是对比类，优先按"维度 -> 差异"组织回答，尽量覆盖主要差异点。
5) 如果问题是机制/流程类，优先按步骤、阶段或关键环节组织回答。
6) 如果问题是字段/结构类，除定义外，尽量补充该字段或结构的作用。
7) 不要把未在上下文中明确出现的信息表述为确定事实。

问题：
{question}

上下文：
{context}
"""

PROMPT_TEMPLATE = PROMPT_TEMPLATE_V2


def _join_context(docs: list[Any]) -> str:
    """将检索到的文档片段用空行拼接为上下文字符串。"""
    return "\n\n".join(doc.page_content for doc in docs)


def build_llm(settings, model_override: str | None = None):
    """构建 ChatOpenAI 实例，支持自定义 base_url。"""
    llm_kwargs = {
        "model": model_override or settings.chat_model,
        "api_key": settings.openai_api_key,
    }
    if settings.openai_base_url:
        llm_kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**llm_kwargs)


def _build_embeddings(settings):
    """构建 OpenAI Embeddings 实例，支持自定义 base_url。"""
    embedding_kwargs = {
        "model": settings.embedding_model,
        "api_key": settings.openai_api_key,
    }
    if settings.openai_base_url:
        embedding_kwargs["base_url"] = settings.openai_base_url
    return OpenAIEmbeddings(**embedding_kwargs)


def health_check() -> dict[str, str | float]:
    """健康检查：分别探测聊天模型和嵌入模型的可用性与延迟。"""
    settings = load_settings()

    t0 = perf_counter()
    t_chat_start = perf_counter()
    build_llm(settings).invoke("请只回复: OK")
    t_chat_end = perf_counter()

    t_embedding_start = perf_counter()
    _build_embeddings(settings).embed_query("network protocol health check")
    t_embedding_end = perf_counter()
    t_total = perf_counter() - t0

    return {
        "status": "ok",
        "chat_model": settings.chat_model,
        "embedding_model": settings.embedding_model,
        "base_url": settings.openai_base_url or "(default)",
        "chat_seconds": t_chat_end - t_chat_start,
        "embedding_seconds": t_embedding_end - t_embedding_start,
        "total_seconds": t_total,
    }


def answer_question(
    question: str,
    progress_callback: Callable[[str], None] | None = None,
    prompt_template: str | None = None,
) -> dict[str, Any]:
    """单次问答：检索上下文 → 流式生成回答，附带各阶段耗时。"""
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
    if not context.strip():  # 检索结果为空，直接返回拒答
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
    prompt = (prompt_template or PROMPT_TEMPLATE).format(question=question, context=context)
    t5_start = perf_counter()
    first_token_seconds: float | None = None
    chunks: list[str] = []
    for chunk in llm.stream(prompt):
        chunk_text = getattr(chunk, "content", "")
        if isinstance(chunk_text, list):
            chunk_text = "".join(str(part) for part in chunk_text)
        if chunk_text:
            if first_token_seconds is None:  # 记录首 token 延迟
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
