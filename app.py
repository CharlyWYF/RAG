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
from src.i18n import t, set_lang
from src.ingest_service import run_ingest
from src.presentation import build_preview_url, format_build_timing_rows, format_timing_rows
from src.qa import health_check
from src.qa_service import AnswerStreamHandler, execute_qa_flow

ENV_PATH = Path(__file__).parent / ".env"

# Sync language from .env (handles runtime config tab changes)
_env_values = read_env_file(ENV_PATH)
set_lang(_env_values.get("UI_LANG", "zh"))
EDITABLE_ENV_KEYS = [
    "UI_LANG",
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
    st.subheader(t("qa.ask"))
    with st.form("qa_form", clear_on_submit=False):
        question = st.text_input(t("qa.enter_question"), placeholder=t("qa.placeholder"))
        ask = st.form_submit_button(t("qa.submit"), type="primary", width="stretch")

    main_status = st.empty()

    if ask:
        if not question.strip():
            st.warning(t("qa.empty_warning"))
        elif len(question) > 1000:
            st.warning(t("qa.too_long_warning"))
        else:
            runtime_logs: list[str] = []

            with main_status.container():
                status_text = st.empty()
                progress_bar = st.progress(0)

            _STAGE_PROGRESS = {
                t("qa.stage_load_config"): 10,
                t("qa.stage_init_retriever"): 30,
                t("qa.stage_retrieve"): 55,
                t("qa.stage_init_llm"): 70,
                t("qa.stage_generate"): 90,
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
                        st.markdown(t("qa.final_answer"))
                        st.caption(t("qa.question_label", question=question.strip()))
                        self.placeholder = st.empty()
                    self.collected_chunks: list[str] = []

                def on_chunk(self, text: str) -> None:
                    self.collected_chunks.append(text)
                    self.placeholder.write("".join(self.collected_chunks))

                def on_first_token(self, seconds: float) -> None:
                    with perf_placeholder.container():
                        st.metric(t("qa.first_token_time"), t("qa.seconds", seconds=seconds))

            try:
                handler = StreamlitAnswerHandler()
                result = execute_qa_flow(
                    question=question.strip(),
                    progress_callback=on_progress,
                    stream_handler=handler,
                )
            except Exception as exc:
                on_progress(t("qa.execution_failed"))
                main_status.error(t("qa.run_failed", exc=exc))
            else:
                progress_bar.progress(100)
                status_text.success(t("qa.gen_done"))
                on_progress(t("qa.exec_done"))
                progress_placeholder.success(t("qa.flow_done"))
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
    st.subheader(t("raw.title"))
    st.caption(t("raw.caption"))

    raw_dir = RAW_DOCS_DIR
    cleaned_dir = CLEANED_DOCS_DIR
    summary = summarize_raw_docs(raw_dir, cleaned_dir)
    docs = summary["docs"]
    cleaned_count = int(summary["cleaned_count"])

    st.markdown(t("raw.dir_status"))

    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.caption(t("raw.doc_count"))
            st.markdown(f"**{len(docs)}**")
    with c2:
        with st.container(border=True):
            st.caption(t("raw.cleaned"))
            st.markdown(f"**{cleaned_count}**")
    with c3:
        with st.container(border=True):
            st.caption(t("raw.uncleaned"))
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
    st.markdown(t("raw.upload_title"))
    st.caption(t("raw.upload_caption"))

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
        t("raw.upload_file"),
        type=["txt", "md", "html", "htm"],
        accept_multiple_files=False,
        key=f"raw_docs_uploader_{uploader_version}",
    )
    overwrite_upload = st.checkbox(
        t("raw.overwrite"),
        value=False,
        key=f"raw_docs_overwrite_{uploader_version}",
    )
    if st.button(t("raw.save_to_raw"), width="stretch", key="save_raw_doc"):
        if upload_file is None:
            upload_status_placeholder.warning(t("raw.select_file_warning"))
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
    st.markdown(t("raw.list_title"))
    st.caption(t("raw.list_caption"))

    if docs:
        rows = build_raw_doc_rows(raw_dir, cleaned_dir)

        with st.container(border=True):
            st.caption(t("raw.file_list"))
            st.dataframe(rows, width="stretch", hide_index=True)

        options = [str(doc.relative_to(raw_dir)) for doc in docs]
        with st.container(border=True):
            st.caption(t("raw.single_clean"))
            selected_raw = st.selectbox(t("raw.select_clean"), options=options, key="clean_single_raw")
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
                st.info(t("raw.existing_info", target=cleaned_target))
            if st.button(t("raw.start_clean"), type="primary", width="stretch", key="process_single_raw"):
                with st.spinner(t("raw.cleaning", file=selected_raw)):
                    ok, message = clean_single_raw_file(raw_dir, cleaned_dir, selected_raw)
                if ok:
                    st.session_state["raw_docs_last_processed"] = {
                        "type": "success",
                        "message": message,
                        "file": selected_raw,
                    }
                    st.toast(t("raw.clean_done", file=selected_raw))
                    st.rerun()
                else:
                    st.session_state["raw_docs_last_processed"] = {
                        "type": "error",
                        "message": message,
                        "file": selected_raw,
                    }
                    status_placeholder.error(message)
    else:
        st.info(t("raw.no_files"))


def _render_kb_tab(progress_placeholder, log_placeholder, perf_placeholder) -> None:
    st.subheader(t("kb.title"))

    try:
        settings = load_settings()
    except Exception as exc:
        st.error(t("kb.config_failed", exc=exc))
        return

    data_dir = Path(settings.data_dir)
    chroma_dir = Path(settings.chroma_dir)

    docs, rows = summarize_kb_source_docs(data_dir)
    chroma_ready = is_chroma_ready(chroma_dir)

    st.markdown(t("kb.current_config"))

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
            st.caption(t("kb.doc_count"))
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
            st.caption(t("kb.data_dir_status"))
            st.markdown(f"**{t('kb.exists') if data_dir.exists() else t('kb.not_exists')}**")
    with s2:
        with st.container(border=True):
            st.caption(t("kb.chroma_status"))
            st.markdown(f"**{t('kb.available') if chroma_ready else t('kb.not_ready')}**")

    st.caption(t("kb.config_caption"))
    st.divider()

    st.markdown(t("kb.file_mgmt_title"))
    st.caption(t("kb.file_mgmt_caption"))
    if not data_dir.exists():
        st.error(t("kb.data_dir_not_exists", dir=data_dir))
    else:
        upload_file = st.file_uploader(
            t("kb.upload_kb_file"),
            type=["md", "txt"],
            accept_multiple_files=False,
        )
        overwrite_upload = st.checkbox(t("kb.overwrite_file"), value=False)
        if st.button(t("kb.save_upload"), width="stretch"):
            if upload_file is None:
                st.warning(t("kb.select_file_warning"))
            else:
                ok, message = save_kb_upload(data_dir, upload_file.name, upload_file.getvalue(), overwrite_upload)
                if ok:
                    st.success(message)
                else:
                    st.warning(message)

        if docs:
            with st.container(border=True):
                st.caption(t("kb.file_list"))
                st.dataframe(rows, width="stretch", hide_index=True)

            with st.container(border=True):
                st.caption(t("kb.delete_file"))
                delete_target = st.selectbox(
                    t("kb.select_delete"),
                    options=[str(doc.relative_to(data_dir)) for doc in docs],
                )
                confirm_delete = st.checkbox(t("kb.confirm_delete"))
                if st.button(t("kb.delete_selected"), width="stretch"):
                    if not confirm_delete:
                        st.warning(t("kb.confirm_warning"))
                    else:
                        ok, message = delete_kb_file(data_dir, delete_target)
                        if ok:
                            st.success(message)
                        else:
                            st.warning(message)
        else:
            st.info(t("kb.no_files"))

    st.divider()
    st.markdown(t("kb.build_title"))
    st.caption(t("kb.build_caption"))
    mode = st.radio(
        t("kb.build_mode"),
        options=["sync", "rebuild", "append"],
        horizontal=True,
        help=t("kb.build_mode_help"),
    )
    chunk_strategy = st.radio(
        t("kb.chunk_strategy"),
        options=["fixed", "section", "hybrid"],
        horizontal=True,
        help=t("kb.chunk_strategy_help"),
    )
    if mode == "rebuild":
        st.warning(t("kb.rebuild_warning"))
    if chunk_strategy == "hybrid":
        st.info(t("kb.hybrid_info"))

    if st.button(t("kb.start_build"), type="primary", width="stretch"):
        build_logs: list[str] = []

        with st.container():
            build_status_placeholder = st.empty()
            build_progress_bar = st.progress(0)

        def on_build_progress(message: str, progress: float | None = None) -> None:
            timestamp = datetime.now().strftime("%H:%M:%S")
            build_logs.append(f"[{timestamp}] {message}")
            build_status_placeholder.info(message)
            progress_placeholder.info(message)
            log_placeholder.code("\n".join(build_logs), language="text")
            if progress is not None:
                safe_progress = max(0.0, min(progress, 1.0))
                build_progress_bar.progress(safe_progress)

        on_build_progress(t("kb.build_start"), 0.01)

        with st.spinner(t("kb.building")):
            stats, _, error_message = run_ingest(
                mode=mode,
                chunk_strategy=chunk_strategy,
                progress_callback=on_build_progress,
            )
            if error_message is not None:
                perf_placeholder.error(t("kb.build_perf_unavail"))
                st.error(t("kb.build_failed", error=error_message))
            else:
                assert stats is not None
                build_progress_bar.progress(1.0)
                build_status_placeholder.success(t("kb.build_done"))
                progress_placeholder.success(t("kb.build_complete"))
                render_build_stats(stats, chunk_strategy, perf_placeholder)


def _render_config_tab() -> None:
    st.subheader(t("config.title"))
    st.caption(t("config.caption"))

    env_values = read_env_file(ENV_PATH)

    try:
        settings = load_settings()
    except Exception as exc:
        settings = None
        st.warning(t("config.not_effective", exc=exc))

    st.markdown(t("config.effective_title"))
    if settings is not None:
        effective_rows = [
            {t("config.item"): "UI_LANG", t("config.value"): str(settings.lang)},
            {t("config.item"): "DATA_DIR", t("config.value"): str(settings.data_dir)},
            {t("config.item"): "CHROMA_DIR", t("config.value"): str(settings.chroma_dir)},
            {t("config.item"): "CHUNK_SIZE", t("config.value"): str(settings.chunk_size)},
            {t("config.item"): "CHUNK_OVERLAP", t("config.value"): str(settings.chunk_overlap)},
            {t("config.item"): "TOP_K", t("config.value"): str(settings.top_k)},
            {t("config.item"): "EMBEDDING_MODEL", t("config.value"): str(settings.embedding_model)},
            {t("config.item"): "CHAT_MODEL", t("config.value"): str(settings.chat_model)},
            {t("config.item"): "QUERY_REWRITE_MODEL", t("config.value"): str(settings.query_rewrite_model)},
            {t("config.item"): "OPENAI_BASE_URL", t("config.value"): str(settings.openai_base_url or t("config.not_set"))},
            {t("config.item"): "OPENAI_API_KEY", t("config.value"): t("config.configured") if settings.openai_api_key else t("config.not_configured")},
        ]
        st.dataframe(effective_rows, width="stretch", hide_index=True)
    else:
        st.info(t("config.cannot_load"))

    st.divider()
    st.markdown(t("config.edit_title"))
    st.caption(t("config.edit_caption"))

    with st.form("env_config_form"):
        current_lang = env_values.get("UI_LANG", "zh")
        lang_options = ["zh", "en"]
        lang_index = 0 if current_lang.strip().lower() != "en" else 1
        lang = st.selectbox("UI_LANG", options=lang_options, index=lang_index)

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
            placeholder=t("config.placeholder_optional"),
        )
        openai_api_key = st.text_input(
            "OPENAI_API_KEY",
            value=env_values.get("OPENAI_API_KEY", ""),
            type="password",
            placeholder=t("config.placeholder_api_key"),
        )

        submit = st.form_submit_button(t("config.save"), type="primary", width="stretch")

    if submit:
        updates = {
            "UI_LANG": lang.strip(),
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
        st.success(t("config.saved"))
        st.rerun()

    with st.expander(t("config.view_env"), expanded=False):
        if ENV_PATH.exists():
            st.code(ENV_PATH.read_text(encoding="utf-8"), language="dotenv")
        else:
            st.info(t("config.no_env"))


st.set_page_config(page_title=t("app.page_title"), layout="wide")
st.title(t("app.title"))
st.caption(t("app.caption"))

with st.sidebar:
    st.header(t("sidebar.title"))
    st.caption(t("sidebar.caption"))

    test_api = st.button(t("sidebar.api_test"), width="stretch")
    api_status_placeholder = st.empty()
    api_detail_placeholder = st.empty()

    st.divider()

    st.subheader(t("sidebar.progress_title"))
    progress_placeholder = st.empty()
    progress_placeholder.caption(t("sidebar.waiting"))

    st.subheader(t("sidebar.log_title"))
    log_placeholder = st.empty()
    log_placeholder.caption(t("sidebar.no_log"))

    st.subheader(t("sidebar.perf_title"))
    perf_placeholder = st.empty()
    perf_placeholder.caption(t("sidebar.no_perf"))

if test_api:
    api_logs = [t("sidebar.api_testing_start")]
    progress_placeholder.info(t("sidebar.api_testing_chat"))
    log_placeholder.code("\n".join(api_logs), language="text")
    with st.spinner(t("sidebar.api_testing")):
        try:
            status = health_check()
        except Exception as exc:
            api_status_placeholder.error(t("sidebar.api_failed"))
            api_detail_placeholder.code(str(exc), language="text")
            progress_placeholder.error(t("sidebar.api_test_failed"))
        else:
            api_logs.append(t("sidebar.api_chat_done"))
            api_logs.append(t("sidebar.api_embed_done"))
            progress_placeholder.success(t("sidebar.api_test_done"))
            log_placeholder.code("\n".join(api_logs), language="text")
            api_status_placeholder.success(t("sidebar.api_ok"))
            api_detail_placeholder.caption(
                f"chat={status['chat_model']} | embedding={status['embedding_model']} | base_url={status['base_url']}"
            )
            with perf_placeholder.container():
                st.metric(t("sidebar.chat_time"), t("qa.seconds", seconds=float(status['chat_seconds'])))
                st.metric(t("sidebar.embed_time"), t("qa.seconds", seconds=float(status['embedding_seconds'])))
                st.metric(t("sidebar.total_time"), t("qa.seconds", seconds=float(status['total_seconds'])))

tab_qa, tab_raw_docs, tab_kb, tab_config = st.tabs([
    t("tab.qa"),
    t("tab.doc_process"),
    t("tab.kb_manage"),
    t("tab.config"),
])

with tab_qa:
    _render_qa_tab(progress_placeholder, log_placeholder, perf_placeholder)

with tab_raw_docs:
    _render_raw_docs_tab()

with tab_kb:
    _render_kb_tab(progress_placeholder, log_placeholder, perf_placeholder)

with tab_config:
    _render_config_tab()
