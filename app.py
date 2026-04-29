from __future__ import annotations

# streamlit_app_label: 问答页面

from time import perf_counter
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from scripts.clean_protocol_docs import process_file
from src.app_views import render_build_stats, render_qa_result
from src.config import load_settings
from src.corpus_service import (
    build_raw_doc_rows,
    clean_single_raw_file,
    delete_kb_file,
    save_kb_upload,
    save_raw_upload,
    summarize_kb_source_docs,
    summarize_raw_docs,
)
from src.file_ops import (
    cleaned_target_for,
    is_chroma_ready,
    is_cleaned,
    list_processable_raw_docs,
    list_raw_docs,
    read_env_file,
    resolve_source_path,
    write_env_file,
)
from src.ingest_service import run_ingest
from src.presentation import build_preview_url, format_build_timing_rows, format_timing_rows
from src.qa import health_check
from src.qa_service import AnswerStreamHandler, execute_qa_flow

ENV_PATH = Path(__file__).parent / ".env"
EDITABLE_ENV_KEYS = [
    "DATA_DIR",
    "CHROMA_DIR",
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "TOP_K",
    "EMBEDDING_MODEL",
    "CHAT_MODEL",
    "QUERY_REWRITE_MODEL",
    "OPENAI_BASE_URL",
]
RAW_DOCS_DIR = Path(__file__).parent / "data" / "protocols" / "raw"
CLEANED_DOCS_DIR = Path(__file__).parent / "data" / "protocols" / "cleaned"


def _render_qa_tab(
    progress_placeholder,
    log_placeholder,
    perf_placeholder,
) -> None:
    st.subheader("提问")
    with st.form("qa_form", clear_on_submit=False):
        question = st.text_input("请输入你的问题", placeholder="例如：TCP 三次握手是什么？")
        ask = st.form_submit_button("开始问答", type="primary", width="stretch")

    main_status = st.empty()

    if ask:
        if not question.strip():
            st.warning("请输入问题后再提问。")
        elif len(question) > 1000:
            st.warning("问题过长，请控制在 1000 字符以内。")
        else:
            runtime_logs: list[str] = []

            with main_status.container():
                status_text = st.empty()
                progress_bar = st.progress(0)

            _STAGE_PROGRESS = {
                "加载配置": 10,
                "初始化检索器": 30,
                "向量检索": 55,
                "初始化大模型": 70,
                "生成最终回答": 90,
            }

            def on_progress(message: str) -> None:
                timestamp = datetime.now().strftime("%H:%M:%S")
                runtime_logs.append(f"[{timestamp}] {message}")
                progress_placeholder.info(message)
                log_placeholder.code("\n".join(runtime_logs), language="text")
                for stage_key, pct in _STAGE_PROGRESS.items():
                    if stage_key in message:
                        progress_bar.progress(pct)
                        break

            class StreamlitAnswerHandler(AnswerStreamHandler):
                def __init__(self) -> None:
                    self.answer_container = st.container(border=True)
                    with self.answer_container:
                        st.markdown("### 最终回答")
                        st.caption(f"问题：{question.strip()}")
                        self.placeholder = st.empty()
                    self.collected_chunks: list[str] = []

                def on_chunk(self, text: str) -> None:
                    self.collected_chunks.append(text)
                    self.placeholder.write("".join(self.collected_chunks))

                def on_first_token(self, seconds: float) -> None:
                    with perf_placeholder.container():
                        st.metric("首字响应时间", f"{seconds:.3f} 秒")

            try:
                handler = StreamlitAnswerHandler()
                result = execute_qa_flow(
                    question=question.strip(),
                    progress_callback=on_progress,
                    stream_handler=handler,
                )
            except Exception as exc:
                on_progress("执行失败。")
                main_status.error(f"运行失败：{exc}")
            else:
                progress_bar.progress(100)
                status_text.success("生成完成。")
                on_progress("执行完成。")
                progress_placeholder.success("问答流程执行完成。")
                main_status.empty()
                st.session_state["qa_last_question"] = question.strip()
                st.session_state["qa_last_result"] = result
                st.rerun()

    stored_question = str(st.session_state.get("qa_last_question", "")).strip()
    stored_result = st.session_state.get("qa_last_result")
    if not stored_question or not isinstance(stored_result, dict):
        return

    render_qa_result(stored_question, stored_result, Path(__file__).parent, perf_placeholder)


def _render_raw_docs_tab() -> None:
    st.subheader("文档处理")
    st.caption("管理 `data/protocols/raw` 下的原始文档，并将单个文件清洗到 `data/protocols/cleaned`。")

    raw_dir = RAW_DOCS_DIR
    cleaned_dir = CLEANED_DOCS_DIR
    summary = summarize_raw_docs(raw_dir, cleaned_dir)
    docs = summary["docs"]
    cleaned_count = int(summary["cleaned_count"])

    st.markdown("### 目录与状态")

    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.caption("原始文档数")
            st.markdown(f"**{len(docs)}**")
    with c2:
        with st.container(border=True):
            st.caption("已清洗")
            st.markdown(f"**{cleaned_count}**")
    with c3:
        with st.container(border=True):
            st.caption("未清洗")
            st.markdown(f"**{len(docs) - cleaned_count}**")

    p1, p2 = st.columns(2)
    with p1:
        with st.container(border=True):
            st.caption("raw_dir")
            st.code(str(raw_dir), language="text")
    with p2:
        with st.container(border=True):
            st.caption("cleaned_dir")
            st.code(str(cleaned_dir), language="text")

    st.divider()
    st.markdown("### 上传原始文档")
    st.caption("支持上传 `.txt`、`.md`、`.html`、`.htm` 到 raw 目录。")

    upload_status_placeholder = st.empty()
    last_upload = st.session_state.get("raw_docs_last_upload")
    if isinstance(last_upload, dict):
        upload_message_type = last_upload.get("type", "success")
        upload_message_text = str(last_upload.get("message", ""))
        if upload_message_text:
            if upload_message_type == "error":
                upload_status_placeholder.error(upload_message_text)
            else:
                upload_status_placeholder.success(upload_message_text)

    uploader_version = int(st.session_state.get("raw_docs_uploader_version", 0))
    upload_file = st.file_uploader(
        "上传原始文件",
        type=["txt", "md", "html", "htm"],
        accept_multiple_files=False,
        key=f"raw_docs_uploader_{uploader_version}",
    )
    overwrite_upload = st.checkbox(
        "允许覆盖同名原始文件",
        value=False,
        key=f"raw_docs_overwrite_{uploader_version}",
    )
    if st.button("保存到 raw 目录", width="stretch", key="save_raw_doc"):
        if upload_file is None:
            upload_status_placeholder.warning("请先选择文件。")
        else:
            ok, message = save_raw_upload(raw_dir, upload_file.name, upload_file.getvalue(), overwrite_upload)
            if ok:
                st.session_state["raw_docs_uploader_version"] = uploader_version + 1
                st.session_state["raw_docs_last_upload"] = {
                    "type": "success",
                    "message": message,
                }
                st.rerun()
            else:
                upload_status_placeholder.warning(message)

    st.divider()
    st.markdown("### 原始文档列表")
    st.caption("查看每个原始文件是否已经清洗，并支持单文件清洗。")

    if docs:
        rows = build_raw_doc_rows(raw_dir, cleaned_dir)

        with st.container(border=True):
            st.caption("文件列表")
            st.dataframe(rows, width="stretch", hide_index=True)

        options = [str(doc.relative_to(raw_dir)) for doc in docs]
        with st.container(border=True):
            st.caption("单文件清洗")
            selected_raw = st.selectbox("选择要清洗的原始文件", options=options, key="clean_single_raw")
            selected_path = raw_dir / selected_raw
            cleaned_target = cleaned_target_for(selected_path, raw_dir, cleaned_dir)
            status_placeholder = st.empty()
            last_processed = st.session_state.get("raw_docs_last_processed")
            should_show_existing_info = cleaned_target.exists()
            if isinstance(last_processed, dict):
                message_type = last_processed.get("type", "success")
                message_text = str(last_processed.get("message", ""))
                last_file = str(last_processed.get("file", ""))
                if message_type == "success" and last_file == selected_raw:
                    should_show_existing_info = False
                if message_text:
                    if message_type == "error":
                        status_placeholder.error(message_text)
                    else:
                        status_placeholder.success(message_text)
            if should_show_existing_info:
                st.info(f"该文件已存在清洗结果，将重新生成：{cleaned_target}")
            if st.button("开始清洗所选文件", type="primary", width="stretch", key="process_single_raw"):
                with st.spinner(f"正在清洗：{selected_raw}"):
                    ok, message = clean_single_raw_file(raw_dir, cleaned_dir, selected_raw)
                if ok:
                    st.session_state["raw_docs_last_processed"] = {
                        "type": "success",
                        "message": message,
                        "file": selected_raw,
                    }
                    st.toast(f"已完成清洗：{selected_raw}")
                    st.rerun()
                else:
                    st.session_state["raw_docs_last_processed"] = {
                        "type": "error",
                        "message": message,
                        "file": selected_raw,
                    }
                    status_placeholder.error(message)
    else:
        st.info("当前 raw 目录下暂无可处理文件。")


def _render_kb_tab(progress_placeholder, log_placeholder, perf_placeholder) -> None:
    st.subheader("知识库与向量库管理")

    try:
        settings = load_settings()
    except Exception as exc:
        st.error(f"配置加载失败：{exc}")
        return

    data_dir = Path(settings.data_dir)
    chroma_dir = Path(settings.chroma_dir)

    docs, rows = summarize_kb_source_docs(data_dir)
    chroma_ready = is_chroma_ready(chroma_dir)

    st.markdown("### 当前配置")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.caption("Chunk Size")
            st.markdown(f"**{settings.chunk_size}**")
    with c2:
        with st.container(border=True):
            st.caption("Chunk Overlap")
            st.markdown(f"**{settings.chunk_overlap}**")
    with c3:
        with st.container(border=True):
            st.caption("TOP_K")
            st.markdown(f"**{settings.top_k}**")
    with c4:
        with st.container(border=True):
            st.caption("原始文档数")
            st.markdown(f"**{len(docs)}**")

    p1, p2 = st.columns(2)
    with p1:
        with st.container(border=True):
            st.caption("data_dir")
            st.code(str(data_dir), language="text")
    with p2:
        with st.container(border=True):
            st.caption("chroma_dir")
            st.code(str(chroma_dir), language="text")

    s1, s2 = st.columns(2)
    with s1:
        with st.container(border=True):
            st.caption("数据目录状态")
            st.markdown(f"**{'存在' if data_dir.exists() else '不存在'}**")
    with s2:
        with st.container(border=True):
            st.caption("向量库状态")
            st.markdown(f"**{'可用' if chroma_ready else '未就绪'}**")

    st.caption("上方卡片展示知识库配置与当前状态。")
    st.divider()

    st.markdown("### 原始文件管理")
    st.caption("上传、查看并删除知识库源文件。")
    if not data_dir.exists():
        st.error(f"数据目录不存在：{data_dir}")
    else:
        upload_file = st.file_uploader(
            "上传 .md 或 .txt 文件",
            type=["md", "txt"],
            accept_multiple_files=False,
        )
        overwrite_upload = st.checkbox("允许覆盖同名文件", value=False)
        if st.button("保存上传文件", width="stretch"):
            if upload_file is None:
                st.warning("请先选择文件。")
            else:
                ok, message = save_kb_upload(data_dir, upload_file.name, upload_file.getvalue(), overwrite_upload)
                if ok:
                    st.success(message)
                else:
                    st.warning(message)

        if docs:
            with st.container(border=True):
                st.caption("文件列表")
                st.dataframe(rows, width="stretch", hide_index=True)

            with st.container(border=True):
                st.caption("删除文件")
                delete_target = st.selectbox(
                    "选择要删除的文件",
                    options=[str(doc.relative_to(data_dir)) for doc in docs],
                )
                confirm_delete = st.checkbox("我确认删除该文件")
                if st.button("删除所选文件", width="stretch"):
                    if not confirm_delete:
                        st.warning("请先勾选删除确认。")
                    else:
                        ok, message = delete_kb_file(data_dir, delete_target)
                        if ok:
                            st.success(message)
                        else:
                            st.warning(message)
        else:
            st.info("当前暂无 .md/.txt 原始文件。")

    st.divider()
    st.markdown("### 向量库构建")
    st.caption("选择构建模式和 chunk 策略后执行向量化。")
    mode = st.radio(
        "构建模式",
        options=["sync", "rebuild", "append"],
        horizontal=True,
        help="sync 会让向量库与当前源文件保持一致；rebuild 会重建；append 仅追加新增 source。",
    )
    chunk_strategy = st.radio(
        "Chunk 策略",
        options=["fixed", "section", "hybrid"],
        horizontal=True,
        help="fixed 为固定长度切分；section 为按 Markdown 标题切分；hybrid 为先按标题切分再对长 section 二次切分。",
    )
    if mode == "rebuild":
        st.warning("rebuild 模式会删除旧向量库后重建，请谨慎操作。")
    if chunk_strategy == "hybrid":
        st.info("hybrid 通常更适合清洗后的 RFC 文档，可兼顾结构信息与 chunk 长度控制。")

    if st.button("开始构建向量库", type="primary", width="stretch"):
        build_progress_bar = st.progress(0, text="等待开始...")
        build_status_placeholder = st.empty()

        def on_build_progress(message: str, progress: float | None = None) -> None:
            build_status_placeholder.info(message)
            progress_placeholder.info(message)
            if progress is not None:
                safe_progress = max(0.0, min(progress, 1.0))
                build_progress_bar.progress(safe_progress, text=f"{int(safe_progress * 100)}%")

        with st.spinner("正在构建向量库..."):
            stats, build_logs, error_message = run_ingest(
                mode=mode,
                chunk_strategy=chunk_strategy,
                progress_callback=on_build_progress,
            )
            log_placeholder.code("\n".join(build_logs), language="text")
            if error_message is not None:
                perf_placeholder.error("构建耗时统计不可用")
                st.error(f"构建失败：{error_message}")
            else:
                assert stats is not None
                render_build_stats(stats, chunk_strategy, perf_placeholder)


def _render_config_tab() -> None:
    st.subheader("系统配置")
    st.caption("查看当前生效配置，并可视化编辑 `.env` 中的关键字段。")

    env_values = read_env_file(ENV_PATH)

    try:
        settings = load_settings()
    except Exception as exc:
        settings = None
        st.warning(f"当前配置未完全生效：{exc}")

    st.markdown("### 当前生效配置")
    if settings is not None:
        effective_rows = [
            {"配置项": "DATA_DIR", "当前值": str(settings.data_dir)},
            {"配置项": "CHROMA_DIR", "当前值": str(settings.chroma_dir)},
            {"配置项": "CHUNK_SIZE", "当前值": str(settings.chunk_size)},
            {"配置项": "CHUNK_OVERLAP", "当前值": str(settings.chunk_overlap)},
            {"配置项": "TOP_K", "当前值": str(settings.top_k)},
            {"配置项": "EMBEDDING_MODEL", "当前值": str(settings.embedding_model)},
            {"配置项": "CHAT_MODEL", "当前值": str(settings.chat_model)},
            {"配置项": "QUERY_REWRITE_MODEL", "当前值": str(settings.query_rewrite_model)},
            {"配置项": "OPENAI_BASE_URL", "当前值": str(settings.openai_base_url or "(未设置)")},
            {"配置项": "OPENAI_API_KEY", "当前值": "已配置" if settings.openai_api_key else "未配置"},
        ]
        st.dataframe(effective_rows, width="stretch", hide_index=True)
    else:
        st.info("当前无法完整加载生效配置，请先检查 `.env`。")

    st.divider()
    st.markdown("### 编辑 `.env` 配置")
    st.caption("保存后，部分配置需要重新建库或刷新页面后生效。")

    with st.form("env_config_form"):
        data_dir = st.text_input("DATA_DIR", value=env_values.get("DATA_DIR", "data/protocols/cleaned"))
        chroma_dir = st.text_input("CHROMA_DIR", value=env_values.get("CHROMA_DIR", "chroma_db"))

        c1, c2, c3 = st.columns(3)
        with c1:
            chunk_size = st.text_input("CHUNK_SIZE", value=env_values.get("CHUNK_SIZE", "1200"))
        with c2:
            chunk_overlap = st.text_input("CHUNK_OVERLAP", value=env_values.get("CHUNK_OVERLAP", "150"))
        with c3:
            top_k = st.text_input("TOP_K", value=env_values.get("TOP_K", "4"))

        embedding_model = st.text_input(
            "EMBEDDING_MODEL",
            value=env_values.get("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        chat_model = st.text_input(
            "CHAT_MODEL",
            value=env_values.get("CHAT_MODEL", "gpt-4o-mini"),
        )
        query_rewrite_model = st.text_input(
            "QUERY_REWRITE_MODEL",
            value=env_values.get("QUERY_REWRITE_MODEL", "gpt-4o-mini"),
        )
        openai_base_url = st.text_input(
            "OPENAI_BASE_URL",
            value=env_values.get("OPENAI_BASE_URL", ""),
            placeholder="可留空",
        )
        openai_api_key = st.text_input(
            "OPENAI_API_KEY",
            value=env_values.get("OPENAI_API_KEY", ""),
            type="password",
            placeholder="请输入 API Key",
        )

        submit = st.form_submit_button("保存配置并刷新页面", type="primary", width="stretch")

    if submit:
        updates = {
            "DATA_DIR": data_dir.strip(),
            "CHROMA_DIR": chroma_dir.strip(),
            "CHUNK_SIZE": chunk_size.strip(),
            "CHUNK_OVERLAP": chunk_overlap.strip(),
            "TOP_K": top_k.strip(),
            "EMBEDDING_MODEL": embedding_model.strip(),
            "CHAT_MODEL": chat_model.strip(),
            "QUERY_REWRITE_MODEL": query_rewrite_model.strip(),
            "OPENAI_BASE_URL": openai_base_url.strip(),
            "OPENAI_API_KEY": openai_api_key.strip(),
        }
        write_env_file(ENV_PATH, updates)
        st.success("`.env` 已更新，正在刷新页面。")
        st.rerun()

    with st.expander("查看 `.env` 原始内容", expanded=False):
        if ENV_PATH.exists():
            st.code(ENV_PATH.read_text(encoding="utf-8"), language="dotenv")
        else:
            st.info("当前不存在 `.env` 文件。")


st.set_page_config(page_title="网络协议问答", layout="wide")
st.title("基于 LLM 的网络协议知识问答")
st.caption("先在`文档处理`中准备和清洗文档，再在`知识库管理`中建库，最后到`问答`中提问。")

with st.sidebar:
    st.header("运行控制台")
    st.caption("API 状态、执行进度、日志和耗时信息")

    test_api = st.button("测试 API 连通性", width="stretch")
    api_status_placeholder = st.empty()
    api_detail_placeholder = st.empty()

    st.divider()

    st.subheader("执行进度")
    progress_placeholder = st.empty()
    progress_placeholder.caption("等待提问...")

    st.subheader("实时日志")
    log_placeholder = st.empty()
    log_placeholder.caption("暂无日志")

    st.subheader("性能指标")
    perf_placeholder = st.empty()
    perf_placeholder.caption("暂无耗时数据")

if test_api:
    api_logs = ["开始测试 API 连通性..."]
    progress_placeholder.info("正在测试 Chat 模型...")
    log_placeholder.code("\n".join(api_logs), language="text")
    with st.spinner("正在测试 API 连通性..."):
        try:
            status = health_check()
        except Exception as exc:
            api_status_placeholder.error("API 连通性测试失败")
            api_detail_placeholder.code(str(exc), language="text")
            progress_placeholder.error("API 测试失败")
        else:
            api_logs.append("Chat 模型测试完成")
            api_logs.append("Embedding 模型测试完成")
            progress_placeholder.success("API 连通性测试完成")
            log_placeholder.code("\n".join(api_logs), language="text")
            api_status_placeholder.success("API 连通性正常")
            api_detail_placeholder.caption(
                f"chat={status['chat_model']} | embedding={status['embedding_model']} | base_url={status['base_url']}"
            )
            with perf_placeholder.container():
                st.metric("Chat 耗时", f"{float(status['chat_seconds']):.3f} 秒")
                st.metric("Embedding 耗时", f"{float(status['embedding_seconds']):.3f} 秒")
                st.metric("总耗时", f"{float(status['total_seconds']):.3f} 秒")

tab_qa, tab_raw_docs, tab_kb, tab_config = st.tabs([
    "问答",
    "文档处理",
    "知识库管理",
    "系统配置",
])

with tab_qa:
    _render_qa_tab(progress_placeholder, log_placeholder, perf_placeholder)

with tab_raw_docs:
    _render_raw_docs_tab()

with tab_kb:
    _render_kb_tab(progress_placeholder, log_placeholder, perf_placeholder)

with tab_config:
    _render_config_tab()
