from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from src.file_ops import resolve_source_path
from src.i18n import t


def stage_label(stage: str) -> str:
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
    rows: list[dict[str, Any]] = []
    for item in timings:
        stage = str(item.get("stage", "unknown"))
        if stage == "first_token":
            continue
        seconds = float(item.get("seconds", 0.0))
        rows.append({t("timing.stage"): stage_label(stage), t("timing.seconds"): round(seconds, 3)})
    return rows


def build_stage_label(stage: str) -> str:
    labels = {
        "load_docs": t("timing.load_docs"),
        "load_chroma": t("timing.load_chroma"),
        "split_docs": t("timing.split_docs"),
        "write_chunks": t("timing.write_chunks"),
        "total": t("timing.total"),
    }
    return labels.get(stage, stage)


def format_build_timing_rows(timings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in timings:
        stage = str(item.get("stage", "unknown"))
        seconds = float(item.get("seconds", 0.0))
        rows.append({t("timing.stage"): build_stage_label(stage), t("timing.seconds"): round(seconds, 3)})
    return rows


def build_preview_url(file_path: str, project_root: Path) -> str:
    resolved = resolve_source_path(file_path, project_root)
    return f"/SourcePreview?path={quote(str(resolved))}"
