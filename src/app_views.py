from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from src.file_ops import resolve_source_path
from src.presentation import build_preview_url, format_build_timing_rows, format_timing_rows


def render_qa_result(stored_question: str, stored_result: dict[str, Any], project_root: Path, perf_placeholder) -> None:
    timings = stored_result.get("timings", [])
    timing_rows = format_timing_rows(timings)
    first_token_seconds = next(
        (
            float(item.get("seconds", 0.0))
            for item in timings
            if str(item.get("stage", "")) == "first_token"
        ),
        0.0,
    )

    with perf_placeholder.container():
        st.metric("首字响应时间", f"{first_token_seconds:.3f} 秒")
        if timing_rows:
            st.dataframe(timing_rows, width="stretch", hide_index=True)

    with st.container(border=True):
        st.markdown("### 最终回答")
        st.caption(f"问题：{stored_question}")
        st.write(stored_result["answer"])

    rewritten_queries = stored_result.get("rewritten_queries", [])
    if isinstance(rewritten_queries, list) and rewritten_queries:
        with st.expander("查询改写", expanded=False):
            st.caption(f"原问题：{stored_question}")
            for idx, query in enumerate(rewritten_queries, start=1):
                st.write(f"{idx}. {query}")

    contexts = stored_result.get("contexts", [])
    sources = stored_result.get("sources", [])
    unique_sources = list(dict.fromkeys(str(src) for src in sources))
    col1, col2 = st.columns(2)
    col1.metric("检索片段数", len(contexts))
    col2.metric("来源文件数", len(unique_sources))

    with st.expander(f"检索片段（{len(contexts)}）", expanded=False):
        if not contexts:
            st.write("无上下文。")
        for idx, ctx in enumerate(contexts, start=1):
            source_name = str(sources[idx - 1]) if idx - 1 < len(sources) else "unknown"
            resolved_source = resolve_source_path(source_name, project_root) if source_name != "unknown" else None
            preview_url = build_preview_url(source_name, project_root) if source_name != "unknown" else ""
            with st.container(border=True):
                st.caption(f"片段 {idx} / {len(contexts)}")
                if source_name != "unknown":
                    source_col, action_col = st.columns([5, 1])
                    with source_col:
                        st.caption(f"来源：{source_name}")
                        if resolved_source is not None:
                            st.caption(f"解析路径：{resolved_source}")
                    with action_col:
                        st.link_button("预览", preview_url, width="stretch")
                else:
                    st.caption(f"来源：{source_name}")
                st.write(ctx)

    with st.expander(f"来源文件（{len(unique_sources)}）", expanded=False):
        if not unique_sources:
            st.write("无来源。")
        else:
            for src in unique_sources:
                resolved_src = resolve_source_path(src, project_root)
                preview_url = build_preview_url(src, project_root)
                src_col, action_col = st.columns([5, 1])
                with src_col:
                    st.write(src)
                    st.caption(f"解析路径：{resolved_src}")
                with action_col:
                    st.link_button("预览", preview_url, use_container_width=True)


def render_build_stats(stats: dict[str, Any], chunk_strategy: str, perf_placeholder) -> None:
    with perf_placeholder.container():
        st.metric("总耗时", f"{float(stats.get('total_seconds', 0.0)):.3f} 秒")
        st.metric("平均每文档耗时", f"{float(stats.get('seconds_per_doc', 0.0)):.3f} 秒")
        timing_items = stats.get("timings", [])
        if isinstance(timing_items, list) and timing_items:
            timing_rows = format_build_timing_rows(timing_items)
            st.dataframe(timing_rows, width="stretch", hide_index=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.caption("模式")
            st.markdown(f"**{stats.get('mode', '-')}**")
    with c2:
        with st.container(border=True):
            st.caption("Chunk 策略")
            st.markdown(f"**{chunk_strategy}**")
    with c3:
        with st.container(border=True):
            st.caption("文档总数")
            st.markdown(f"**{int(stats.get('docs_total', 0))}**")
    with c4:
        with st.container(border=True):
            st.caption("写入文档数")
            st.markdown(f"**{int(stats.get('docs_indexed', 0))}**")

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        with st.container(border=True):
            st.caption("跳过文档数")
            st.markdown(f"**{int(stats.get('skipped_docs', 0))}**")
    with d2:
        with st.container(border=True):
            st.caption("新增文档")
            st.markdown(f"**{int(stats.get('added_docs', 0))}**")
    with d3:
        with st.container(border=True):
            st.caption("更新文档")
            st.markdown(f"**{int(stats.get('updated_docs', 0))}**")
    with d4:
        with st.container(border=True):
            st.caption("删除文档")
            st.markdown(f"**{int(stats.get('deleted_docs', 0))}**")

    e1, e2, e3, e4 = st.columns(4)
    with e1:
        with st.container(border=True):
            st.caption("未变化文档")
            st.markdown(f"**{int(stats.get('unchanged_docs', 0))}**")
    with e2:
        with st.container(border=True):
            st.caption("写入 Chunk")
            st.markdown(f"**{int(stats.get('chunks_written', 0))}**")
    with e3:
        with st.container(border=True):
            st.caption("删除 Chunk")
            st.markdown(f"**{int(stats.get('deleted_chunks', 0))}**")
    with e4:
        with st.container(border=True):
            st.caption("持久化目录")
            st.code(str(stats.get("persist_dir", "-")), language="text")
