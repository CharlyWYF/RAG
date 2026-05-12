from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.clean_protocol_docs import process_file
from src.file_ops import cleaned_target_for, list_processable_raw_docs, list_raw_docs
from src.i18n import t


def summarize_raw_docs(raw_dir: Path, cleaned_dir: Path) -> dict[str, Any]:
    docs = list_processable_raw_docs(raw_dir)
    cleaned_count = sum(1 for doc in docs if cleaned_target_for(doc, raw_dir, cleaned_dir).exists())
    return {
        "docs": docs,
        "cleaned_count": cleaned_count,
        "uncleaned_count": len(docs) - cleaned_count,
    }


def save_raw_upload(raw_dir: Path, file_name: str, content: bytes, overwrite: bool) -> tuple[bool, str]:
    target = raw_dir / file_name
    if target.exists() and not overwrite:
        return False, t("raw.upload_exists")
    raw_dir.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return True, t("raw.upload_success", file=file_name)


def build_raw_doc_rows(raw_dir: Path, cleaned_dir: Path) -> list[dict[str, Any]]:
    docs = list_processable_raw_docs(raw_dir)
    rows = []
    for doc in docs:
        rel = doc.relative_to(raw_dir)
        cleaned_target = cleaned_target_for(doc, raw_dir, cleaned_dir)
        stat = doc.stat()
        rows.append(
            {
                t("raw.col_file"): str(rel),
                t("raw.col_size"): round(stat.st_size / 1024, 2),
                t("raw.col_mtime"): datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                t("raw.col_status"): t("raw.status_cleaned") if cleaned_target.exists() else t("raw.status_uncleaned"),
                t("raw.col_cleaned_file"): str(cleaned_target.relative_to(cleaned_dir)),
            }
        )
    return rows


def clean_single_raw_file(raw_dir: Path, cleaned_dir: Path, selected_raw: str) -> tuple[bool, str]:
    selected_path = raw_dir / selected_raw
    try:
        target = process_file(selected_path, raw_dir, cleaned_dir)
    except Exception as exc:
        return False, t("raw.clean_failed", exc=exc)
    return True, t("raw.clean_result", file=selected_raw, target=target.relative_to(cleaned_dir))


def summarize_kb_source_docs(data_dir: Path) -> tuple[list[Path], list[dict[str, Any]]]:
    docs = list_raw_docs(data_dir) if data_dir.exists() else []
    rows = []
    for doc in docs:
        rel = doc.relative_to(data_dir)
        stat = doc.stat()
        rows.append(
            {
                t("kb.col_file"): str(rel),
                t("kb.col_size"): round(stat.st_size / 1024, 2),
                t("kb.col_mtime"): datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return docs, rows


def save_kb_upload(data_dir: Path, file_name: str, content: bytes, overwrite: bool) -> tuple[bool, str]:
    target = data_dir / file_name
    if target.exists() and not overwrite:
        return False, t("kb.upload_exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return True, t("kb.upload_success", target=target)


def delete_kb_file(data_dir: Path, delete_target: str) -> tuple[bool, str]:
    target = data_dir / delete_target
    if not target.exists():
        return False, t("kb.file_not_found")
    target.unlink()
    return True, t("kb.file_deleted", target=target)
