from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from src.file_ops import resolve_source_path
from src.i18n import t
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
        st.metric(t("qa.result.first_token"), t("qa.result.seconds", seconds=first_token_seconds))
        if timing_rows:
            st.dataframe(timing_rows, width="stretch", hide_index=True)

    with st.container(border=True):
        st.markdown(t("qa.result.final_answer"))
        st.caption(t("qa.result.question", question=stored_question))
        st.write(stored_result["answer"])

    rewritten_queries = stored_result.get("rewritten_queries", [])
    if isinstance(rewritten_queries, list) and rewritten_queries:
        with st.expander(t("qa.result.query_rewrite"), expanded=False):
            st.caption(t("qa.result.original_question", question=stored_question))
            for idx, query in enumerate(rewritten_queries, start=1):
                st.write(f"{idx}. {query}")

    contexts = stored_result.get("contexts", [])
    sources = stored_result.get("sources", [])
    unique_sources = list(dict.fromkeys(str(src) for src in sources))
    col1, col2 = st.columns(2)
    col1.metric(t("qa.result.context_count"), len(contexts))
    col2.metric(t("qa.result.source_count"), len(unique_sources))

    with st.expander(t("qa.result.contexts", count=len(contexts)), expanded=False):
        if not contexts:
            st.write(t("qa.result.no_context"))
        for idx, ctx in enumerate(contexts, start=1):
            source_name = str(sources[idx - 1]) if idx - 1 < len(sources) else "unknown"
            resolved_source = resolve_source_path(source_name, project_root) if source_name != "unknown" else None
            preview_url = build_preview_url(source_name, project_root) if source_name != "unknown" else ""
            with st.container(border=True):
                st.caption(t("qa.result.chunk_idx", idx=idx, total=len(contexts)))
                if source_name != "unknown":
                    source_col, action_col = st.columns([5, 1])
                    with source_col:
                        st.caption(t("qa.result.source", source=source_name))
                        if resolved_source is not None:
                            st.caption(t("qa.result.resolved_path", path=resolved_source))
                    with action_col:
                        st.link_button(t("qa.result.preview"), preview_url, width="stretch")
                else:
                    st.caption(t("qa.result.source", source=source_name))
                st.write(ctx)

    with st.expander(t("qa.result.source_files", count=len(unique_sources)), expanded=False):
        if not unique_sources:
            st.write(t("qa.result.no_source"))
        else:
            for src in unique_sources:
                resolved_src = resolve_source_path(src, project_root)
                preview_url = build_preview_url(src, project_root)
                src_col, action_col = st.columns([5, 1])
                with src_col:
                    st.write(src)
                    st.caption(t("qa.result.resolved_path", path=resolved_src))
                with action_col:
                    st.link_button(t("qa.result.preview"), preview_url, use_container_width=True)


def render_build_stats(stats: dict[str, Any], chunk_strategy: str, perf_placeholder) -> None:
    with perf_placeholder.container():
        st.metric(t("build.total_time"), t("build.seconds", seconds=float(stats.get("total_seconds", 0.0))))
        st.metric(t("build.per_doc_time"), t("build.seconds", seconds=float(stats.get("seconds_per_doc", 0.0))))
        timing_items = stats.get("timings", [])
        if isinstance(timing_items, list) and timing_items:
            timing_rows = format_build_timing_rows(timing_items)
            st.dataframe(timing_rows, width="stretch", hide_index=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.caption(t("build.mode"))
            st.markdown(f"**{stats.get('mode', '-')}**")
    with c2:
        with st.container(border=True):
            st.caption(t("build.chunk_strategy"))
            st.markdown(f"**{chunk_strategy}**")
    with c3:
        with st.container(border=True):
            st.caption(t("build.doc_total"))
            st.markdown(f"**{int(stats.get('docs_total', 0))}**")
    with c4:
        with st.container(border=True):
            st.caption(t("build.docs_indexed"))
            st.markdown(f"**{int(stats.get('docs_indexed', 0))}**")

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        with st.container(border=True):
            st.caption(t("build.skipped"))
            st.markdown(f"**{int(stats.get('skipped_docs', 0))}**")
    with d2:
        with st.container(border=True):
            st.caption(t("build.added"))
            st.markdown(f"**{int(stats.get('added_docs', 0))}**")
    with d3:
        with st.container(border=True):
            st.caption(t("build.updated"))
            st.markdown(f"**{int(stats.get('updated_docs', 0))}**")
    with d4:
        with st.container(border=True):
            st.caption(t("build.deleted"))
            st.markdown(f"**{int(stats.get('deleted_docs', 0))}**")

    e1, e2, e3, e4 = st.columns(4)
    with e1:
        with st.container(border=True):
            st.caption(t("build.unchanged"))
            st.markdown(f"**{int(stats.get('unchanged_docs', 0))}**")
    with e2:
        with st.container(border=True):
            st.caption(t("build.chunks_written"))
            st.markdown(f"**{int(stats.get('chunks_written', 0))}**")
    with e3:
        with st.container(border=True):
            st.caption(t("build.chunks_deleted"))
            st.markdown(f"**{int(stats.get('deleted_chunks', 0))}**")
    with e4:
        with st.container(border=True):
            st.caption(t("build.persist_dir"))
            st.code(str(stats.get("persist_dir", "-")), language="text")
