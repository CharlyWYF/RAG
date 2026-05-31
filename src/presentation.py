"""展示层：格式化耗时数据与构建预览链接。"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from src.file_ops import resolve_source_path
from src.i18n import t


def stage_label(stage: str) -> str:
    """查询阶段的中文/本地化标签映射。"""
    labels = {
        "load_settings": t("timing.load_config"),
        "rewrite_query": t("timing.rewrite_query"),
        "init_retriever": t("timing.init_retriever"),
        "retrieve": t("timing.retrieve"),
        "init_llm": t("timing.init_llm"),
        "first_token": t("timing.first_token"),
        "generate_first_token": t("timing.gen_first_token"),
        "generate_answer": t("timing.generate_answer"),
        "total": t("timing.total"),
    }
    return labels.get(stage, stage)


def format_timing_rows(timings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将原始计时数据转为展示用的行列表。"""
    rows: list[dict[str, Any]] = []
    for item in timings:
        stage = str(item.get("stage", "unknown"))
        if stage == "first_token":
            continue  # 首token仅用于内部计算，不单独展示
        seconds = float(item.get("seconds", 0.0))
        rows.append({t("timing.stage"): stage_label(stage), t("timing.seconds"): round(seconds, 3)})
    return rows


def build_stage_label(stage: str) -> str:
    """索引构建阶段的中文/本地化标签映射。"""
    labels = {
        "load_docs": t("timing.load_docs"),
        "load_chroma": t("timing.load_chroma"),
        "split_docs": t("timing.split_docs"),
        "write_chunks": t("timing.write_chunks"),
        "total": t("timing.total"),
    }
    return labels.get(stage, stage)


def format_build_timing_rows(timings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将索引构建的原始计时数据转为展示用的行列表。"""
    rows: list[dict[str, Any]] = []
    for item in timings:
        stage = str(item.get("stage", "unknown"))
        seconds = float(item.get("seconds", 0.0))
        rows.append({t("timing.stage"): build_stage_label(stage), t("timing.seconds"): round(seconds, 3)})
    return rows


def build_preview_url(file_path: str, project_root: Path) -> str:
    """根据文件路径构建 SourcePreview 的查询 URL。"""
    resolved = resolve_source_path(file_path, project_root)
    return f"/SourcePreview?path={quote(str(resolved))}"
