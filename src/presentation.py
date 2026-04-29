from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from src.file_ops import resolve_source_path


def stage_label(stage: str) -> str:
    labels = {
        "load_settings": "加载配置",
        "rewrite_query": "查询改写",
        "init_retriever": "初始化检索器",
        "retrieve": "向量检索",
        "init_llm": "初始化大模型客户端",
        "first_token": "首字响应时间",
        "generate_first_token": "生成首字耗时",
        "generate_answer": "生成回答",
        "total": "总耗时",
    }
    return labels.get(stage, stage)


def format_timing_rows(timings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in timings:
        stage = str(item.get("stage", "unknown"))
        if stage == "first_token":
            continue
        seconds = float(item.get("seconds", 0.0))
        rows.append({"阶段": stage_label(stage), "耗时(秒)": round(seconds, 3)})
    return rows


def build_stage_label(stage: str) -> str:
    labels = {
        "load_docs": "加载文档",
        "load_chroma": "加载向量库",
        "split_docs": "文档切块",
        "write_chunks": "写入 Chunk / Embedding",
        "total": "总耗时",
    }
    return labels.get(stage, stage)


def format_build_timing_rows(timings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in timings:
        stage = str(item.get("stage", "unknown"))
        seconds = float(item.get("seconds", 0.0))
        rows.append({"阶段": build_stage_label(stage), "耗时(秒)": round(seconds, 3)})
    return rows


def build_preview_url(file_path: str, project_root: Path) -> str:
    resolved = resolve_source_path(file_path, project_root)
    return f"/来源预览?path={quote(str(resolved))}"
