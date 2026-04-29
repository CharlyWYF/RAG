from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.clean_protocol_docs import process_file
from src.file_ops import cleaned_target_for, list_processable_raw_docs, list_raw_docs


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
        return False, "存在同名文件，请勾选“允许覆盖同名原始文件”后重试。"
    raw_dir.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return True, f"原始文件上传成功：{file_name}"


def build_raw_doc_rows(raw_dir: Path, cleaned_dir: Path) -> list[dict[str, Any]]:
    docs = list_processable_raw_docs(raw_dir)
    rows = []
    for doc in docs:
        rel = doc.relative_to(raw_dir)
        cleaned_target = cleaned_target_for(doc, raw_dir, cleaned_dir)
        stat = doc.stat()
        rows.append(
            {
                "原始文件": str(rel),
                "大小(KB)": round(stat.st_size / 1024, 2),
                "修改时间": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "清洗状态": "已清洗" if cleaned_target.exists() else "未清洗",
                "cleaned 文件": str(cleaned_target.relative_to(cleaned_dir)),
            }
        )
    return rows


def clean_single_raw_file(raw_dir: Path, cleaned_dir: Path, selected_raw: str) -> tuple[bool, str]:
    selected_path = raw_dir / selected_raw
    try:
        target = process_file(selected_path, raw_dir, cleaned_dir)
    except Exception as exc:
        return False, f"清洗失败：{exc}"
    return True, f"清洗完成：{selected_raw} -> {target.relative_to(cleaned_dir)}"


def summarize_kb_source_docs(data_dir: Path) -> tuple[list[Path], list[dict[str, Any]]]:
    docs = list_raw_docs(data_dir) if data_dir.exists() else []
    rows = []
    for doc in docs:
        rel = doc.relative_to(data_dir)
        stat = doc.stat()
        rows.append(
            {
                "文件": str(rel),
                "大小(KB)": round(stat.st_size / 1024, 2),
                "修改时间": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return docs, rows


def save_kb_upload(data_dir: Path, file_name: str, content: bytes, overwrite: bool) -> tuple[bool, str]:
    target = data_dir / file_name
    if target.exists() and not overwrite:
        return False, "存在同名文件，请勾选“允许覆盖同名文件”后重试。"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return True, f"文件已保存：{target}"


def delete_kb_file(data_dir: Path, delete_target: str) -> tuple[bool, str]:
    target = data_dir / delete_target
    if not target.exists():
        return False, "文件不存在，可能已被删除。"
    target.unlink()
    return True, f"已删除：{target}"
