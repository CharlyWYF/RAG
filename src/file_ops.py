from __future__ import annotations

from pathlib import Path

RAW_DOC_SUFFIXES = {".txt", ".md", ".html", ".htm"}


def read_env_file(env_path: Path) -> dict[str, str]:
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


def write_env_file(env_path: Path, updates: dict[str, str]) -> None:
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


def list_raw_docs(data_dir: Path) -> list[Path]:
    files = list(data_dir.rglob("*.md")) + list(data_dir.rglob("*.txt"))
    return sorted(files, key=lambda p: str(p.relative_to(data_dir)).lower())


def list_processable_raw_docs(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        return []
    files = [
        path
        for path in data_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in RAW_DOC_SUFFIXES
    ]
    return sorted(files, key=lambda p: str(p.relative_to(data_dir)).lower())


def cleaned_target_for(raw_file: Path, raw_base: Path, cleaned_base: Path) -> Path:
    return cleaned_base / raw_file.relative_to(raw_base).with_suffix(".md")


def is_cleaned(raw_file: Path, raw_base: Path, cleaned_base: Path) -> bool:
    return cleaned_target_for(raw_file, raw_base, cleaned_base).exists()


def is_chroma_ready(chroma_dir: Path) -> bool:
    return (chroma_dir / "chroma.sqlite3").exists()


def resolve_source_path(file_path: str, project_root: Path) -> Path:
    normalized = file_path.replace("\\", "/").strip()
    path = Path(normalized).expanduser()
    if path.is_absolute():
        return path.resolve()

    path_str = path.as_posix()
    if path_str.startswith("data/"):
        return (project_root / path_str).resolve()

    return (project_root / path).resolve()
