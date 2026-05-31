"""文件与路径工具：环境文件读写、文档清单、路径解析等。"""
from __future__ import annotations

from pathlib import Path

# 可被 ingest 流水线处理的原始文档后缀
RAW_DOC_SUFFIXES = {".txt", ".md", ".html", ".htm"}


def read_env_file(env_path: Path) -> dict[str, str]:
    """读取 .env 文件，返回 key=value 字典。"""
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:  # 跳过空行、注释、无等号行
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def write_env_file(env_path: Path, updates: dict[str, str]) -> None:
    """更新 .env 文件：已有 key 就地替换，新增 key 追加到末尾。"""
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated_keys: set[str] = set()
    new_lines: list[str] = []

    for raw_line in existing_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            new_lines.append(raw_line)  # 保留空行、注释行原样
            continue

        key, _ = raw_line.split("=", 1)
        normalized_key = key.strip()
        if normalized_key in updates:
            new_lines.append(f"{normalized_key}={updates[normalized_key]}")
            updated_keys.add(normalized_key)
        else:
            new_lines.append(raw_line)

    for key, value in updates.items():
        if key not in updated_keys:  # 文件中不存在的 key 追加到末尾
            new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def list_raw_docs(data_dir: Path) -> list[Path]:
    """列出 data_dir 下所有 .md / .txt 文件（按相对路径排序）。"""
    files = list(data_dir.rglob("*.md")) + list(data_dir.rglob("*.txt"))
    return sorted(files, key=lambda p: str(p.relative_to(data_dir)).lower())


def list_processable_raw_docs(data_dir: Path) -> list[Path]:
    """列出 data_dir 下所有可处理的原始文档（含 .html/.htm）。"""
    if not data_dir.exists():
        return []
    files = [
        path
        for path in data_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in RAW_DOC_SUFFIXES
    ]
    return sorted(files, key=lambda p: str(p.relative_to(data_dir)).lower())


def cleaned_target_for(raw_file: Path, raw_base: Path, cleaned_base: Path) -> Path:
    """计算原始文件对应的清洗后 .md 输出路径。"""
    return cleaned_base / raw_file.relative_to(raw_base).with_suffix(".md")


def is_cleaned(raw_file: Path, raw_base: Path, cleaned_base: Path) -> bool:
    """判断原始文件是否已被清洗（对应 .md 输出是否存在）。"""
    return cleaned_target_for(raw_file, raw_base, cleaned_base).exists()


def is_chroma_ready(chroma_dir: Path) -> bool:
    """判断 ChromaDB 数据目录是否已初始化（sqlite3 文件是否存在）。"""
    return (chroma_dir / "chroma.sqlite3").exists()


def resolve_source_path(file_path: str, project_root: Path) -> Path:
    """将用户输入的文件路径解析为绝对路径。支持 ~、绝对路径、data/ 前缀的相对路径。"""
    normalized = file_path.replace("\\", "/").strip()
    path = Path(normalized).expanduser()
    if path.is_absolute():
        return path.resolve()

    path_str = path.as_posix()
    if path_str.startswith("data/"):
        return (project_root / path_str).resolve()

    return (project_root / path).resolve()
