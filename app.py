from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from src.config import load_settings
from src.ingest import build_index
from src.qa import answer_question, health_check

ENV_PATH = Path(__file__).parent / ".env"
EDITABLE_ENV_KEYS = [
    "DATA_DIR",
    "CHROMA_DIR",
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "TOP_K",
    "EMBEDDING_MODEL",
    "CHAT_MODEL",
    "OPENAI_BASE_URL",
]


def _read_env_file(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _write_env_file(env_path: Path, updates: dict[str, str]) -> None:
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated_keys: set[str] = set()
    new_lines: list[str] = []

    for raw_line in existing_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            new_lines.append(raw_line)
            continue

        key, _ = raw_line.split("=", 1)
        normalized_key = key.strip()
        if normalized_key in updates:
            new_lines.append(f"{normalized_key}={updates[normalized_key]}")
            updated_keys.add(normalized_key)
        else:
            new_lines.append(raw_line)

    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def _stage_label(stage: str) -> str:
    labels = {
        "load_settings": "加载配置",
        "init_retriever": "初始化检索器",
        "retrieve": "向量检索",
        "init_llm": "初始化大模型客户端",
        "generate_answer": "生成回答",
        "total": "端到端总耗时",
    }
    return labels.get(stage, stage)


def _format_timing_rows(timings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in timings:
        stage = str(item.get("stage", "unknown"))
        seconds = float(item.get("seconds", 0.0))
        rows.append({"阶段": _stage_label(stage), "耗时(秒)": round(seconds, 3)})
    return rows


def _list_raw_docs(data_dir: Path) -> list[Path]:
    files = list(data_dir.rglob("*.md")) + list(data_dir.rglob("*.txt"))
    return sorted(files, key=lambda p: str(p.relative_to(data_dir)).lower())


def _is_chroma_ready(chroma_dir: Path) -> bool:
    return (chroma_dir / "chroma.sqlite3").exists()


def _render_qa_tab(
    progress_placeholder,
    log_placeholder,
    perf_placeholder,
) -> None:
    st.subheader("提问")
    with st.form("qa_form", clear_on_submit=False):
        question = st.text_input("请输入你的问题", placeholder="例如：TCP 三次握手是什么？")
        ask = st.form_submit_button("开始问答", type="primary", use_container_width=True)

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

            on_progress("开始执行问答流程...")
            status_text.info("答案生成中，请稍候...")
            progress_bar.progress(5)

            try:
                result = answer_question(question.strip(), progress_callback=on_progress)
            except Exception as exc:
                on_progress("执行失败。")
                main_status.error(f"运行失败：{exc}")
            else:
                progress_bar.progress(100)
                status_text.success("生成完成。")
                on_progress("执行完成。")
                progress_placeholder.success("问答流程执行完成。")
                main_status.empty()

                timings = result.get("timings", [])
                total_seconds = float(result.get("total_seconds", 0.0))
                timing_rows = _format_timing_rows(timings)

                with perf_placeholder.container():
                    st.metric("端到端总耗时", f"{total_seconds:.3f} 秒")
                    if timing_rows:
                        st.dataframe(timing_rows, use_container_width=True, hide_index=True)

                with st.container(border=True):
                    st.markdown("### 最终回答")
                    st.caption(f"问题：{question.strip()}")
                    st.write(result["answer"])

                contexts = result.get("contexts", [])
                sources = result.get("sources", [])
                col1, col2 = st.columns(2)
                col1.metric("检索片段数", len(contexts))
                col2.metric("来源文件数", len(sources))

                with st.expander(f"检索片段（{len(contexts)}）", expanded=False):
                    if not contexts:
                        st.write("无上下文。")
                    for idx, ctx in enumerate(contexts, start=1):
                        with st.container(border=True):
                            st.caption(f"片段 {idx} / {len(contexts)}")
                            st.write(ctx)

                with st.expander(f"来源文件（{len(sources)}）", expanded=False):
                    if not sources:
                        st.write("无来源。")
                    for src in sources:
                        st.write(src)


def _render_kb_tab() -> None:
    st.subheader("知识库与向量库管理")

    try:
        settings = load_settings()
    except Exception as exc:
        st.error(f"配置加载失败：{exc}")
        return

    data_dir = Path(settings.data_dir)
    chroma_dir = Path(settings.chroma_dir)

    docs = _list_raw_docs(data_dir) if data_dir.exists() else []
    chroma_ready = _is_chroma_ready(chroma_dir)

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
        if st.button("保存上传文件", use_container_width=True):
            if upload_file is None:
                st.warning("请先选择文件。")
            else:
                target = data_dir / upload_file.name
                if target.exists() and not overwrite_upload:
                    st.warning("存在同名文件，请勾选“允许覆盖同名文件”后重试。")
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(upload_file.getvalue())
                    st.success(f"文件已保存：{target}")

        if docs:
            rows = []
            for doc in docs:
                rel = doc.relative_to(data_dir)
                stat = doc.stat()
                rows.append(
                    {
                        "文件": str(rel),
                        "大小(KB)": round(stat.st_size / 1024, 2),
                        "修改时间": datetime.fromtimestamp(stat.st_mtime).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            with st.container(border=True):
                st.caption("文件列表")
                st.dataframe(rows, use_container_width=True, hide_index=True)

            with st.container(border=True):
                st.caption("删除文件")
                delete_target = st.selectbox(
                    "选择要删除的文件",
                    options=[str(doc.relative_to(data_dir)) for doc in docs],
                )
                confirm_delete = st.checkbox("我确认删除该文件")
                if st.button("删除所选文件", use_container_width=True):
                    if not confirm_delete:
                        st.warning("请先勾选删除确认。")
                    else:
                        target = data_dir / delete_target
                        if target.exists():
                            target.unlink()
                            st.success(f"已删除：{target}")
                        else:
                            st.warning("文件不存在，可能已被删除。")
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

    if st.button("开始构建向量库", type="primary", use_container_width=True):
        build_progress_bar = st.progress(0, text="等待开始...")
        build_progress_placeholder = st.empty()
        build_log_placeholder = st.empty()
        build_logs: list[str] = []

        def on_build_progress(message: str, progress: float | None = None) -> None:
            timestamp = datetime.now().strftime("%H:%M:%S")
            build_logs.append(f"[{timestamp}] {message}")
            build_progress_placeholder.info(message)
            if progress is not None:
                safe_progress = max(0.0, min(progress, 1.0))
                build_progress_bar.progress(safe_progress, text=f"{int(safe_progress * 100)}%")
            build_log_placeholder.code("\n".join(build_logs), language="text")

        with st.spinner("正在构建向量库..."):
            try:
                on_build_progress("开始执行向量库构建...", 0.01)
                stats = build_index(
                    mode=mode,
                    chunk_strategy=chunk_strategy,
                    progress_callback=on_build_progress,
                )
            except Exception as exc:
                on_build_progress("向量库构建失败。", 1.0)
                st.error(f"构建失败：{exc}")
            else:
                on_build_progress("向量库构建完成。", 1.0)

                c7, c8, c9, c10 = st.columns(4)
                with c7:
                    with st.container(border=True):
                        st.caption("模式")
                        st.markdown(f"**{stats.get('mode', '-')}**")
                with c8:
                    with st.container(border=True):
                        st.caption("Chunk 策略")
                        st.markdown(f"**{chunk_strategy}**")
                with c9:
                    with st.container(border=True):
                        st.caption("文档总数")
                        st.markdown(f"**{int(stats.get('docs_total', 0))}**")
                with c10:
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


def _render_config_tab() -> None:
    st.subheader("系统配置")
    st.caption("查看当前生效配置，并可视化编辑 `.env` 中的关键字段。")

    env_values = _read_env_file(ENV_PATH)

    try:
        settings = load_settings()
    except Exception as exc:
        settings = None
        st.warning(f"当前配置未完全生效：{exc}")

    st.markdown("### 当前生效配置")
    if settings is not None:
        effective_rows = [
            {"配置项": "DATA_DIR", "当前值": settings.data_dir},
            {"配置项": "CHROMA_DIR", "当前值": settings.chroma_dir},
            {"配置项": "CHUNK_SIZE", "当前值": settings.chunk_size},
            {"配置项": "CHUNK_OVERLAP", "当前值": settings.chunk_overlap},
            {"配置项": "TOP_K", "当前值": settings.top_k},
            {"配置项": "EMBEDDING_MODEL", "当前值": settings.embedding_model},
            {"配置项": "CHAT_MODEL", "当前值": settings.chat_model},
            {"配置项": "OPENAI_BASE_URL", "当前值": settings.openai_base_url or "(未设置)"},
            {"配置项": "OPENAI_API_KEY", "当前值": "已配置" if settings.openai_api_key else "未配置"},
        ]
        st.dataframe(effective_rows, use_container_width=True, hide_index=True)
    else:
        st.info("当前无法完整加载生效配置，请先检查 `.env`。")

    st.divider()
    st.markdown("### 编辑 `.env` 配置")
    st.caption("保存后，部分配置需要重新建库或刷新页面后生效。")

    with st.form("env_config_form"):
        data_dir = st.text_input("DATA_DIR", value=env_values.get("DATA_DIR", "data/protocols"))
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

        submit = st.form_submit_button("保存配置并刷新页面", type="primary", use_container_width=True)

    if submit:
        updates = {
            "DATA_DIR": data_dir.strip(),
            "CHROMA_DIR": chroma_dir.strip(),
            "CHUNK_SIZE": chunk_size.strip(),
            "CHUNK_OVERLAP": chunk_overlap.strip(),
            "TOP_K": top_k.strip(),
            "EMBEDDING_MODEL": embedding_model.strip(),
            "CHAT_MODEL": chat_model.strip(),
            "OPENAI_BASE_URL": openai_base_url.strip(),
            "OPENAI_API_KEY": openai_api_key.strip(),
        }
        _write_env_file(ENV_PATH, updates)
        st.success("`.env` 已更新，正在刷新页面。")
        st.rerun()

    with st.expander("查看 `.env` 原始内容", expanded=False):
        if ENV_PATH.exists():
            st.code(ENV_PATH.read_text(encoding="utf-8"), language="dotenv")
        else:
            st.info("当前不存在 `.env` 文件。")


st.set_page_config(page_title="RAG 网络协议问答", layout="wide")
st.title("基于 RAG 的网络协议知识问答")
st.caption("先在`知识库管理`中建库，再在`问答`中提问。")

with st.sidebar:
    st.header("运行控制台")
    st.caption("API 状态、执行进度、日志和耗时信息")

    test_api = st.button("测试 API 连通性", use_container_width=True)
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
    with st.spinner("正在测试 API 连通性..."):
        try:
            status = health_check()
        except Exception as exc:
            api_status_placeholder.error("API 连通性测试失败")
            api_detail_placeholder.code(str(exc), language="text")
        else:
            api_status_placeholder.success("API 连通性正常")
            api_detail_placeholder.caption(
                f"chat={status['chat_model']} | embedding={status['embedding_model']} | base_url={status['base_url']}"
            )

tab_qa, tab_kb, tab_config = st.tabs(["问答", "知识库管理", "系统配置"])

with tab_qa:
    _render_qa_tab(progress_placeholder, log_placeholder, perf_placeholder)

with tab_kb:
    _render_kb_tab()

with tab_config:
    _render_config_tab()
