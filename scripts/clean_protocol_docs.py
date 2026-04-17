#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对 RFC 协议文档做轻量清洗，输出更适合 RAG 的文本。"""
from __future__ import annotations

import html
import io
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

RAW_DIR = Path(__file__).parent.parent / "data" / "protocols"
CLEAN_DIR = RAW_DIR / "cleaned"

SKIP_LINE_PATTERNS = [
    re.compile(r"^\s*Page\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*RFC\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*Network Working Group\s*$", re.IGNORECASE),
    re.compile(r"^\s*Request for Comments:\s*\d+", re.IGNORECASE),
    re.compile(r"^\s*Category:\s*", re.IGNORECASE),
    re.compile(r"^\s*ISSN:\s*", re.IGNORECASE),
    re.compile(r"^\s*STD:\s*", re.IGNORECASE),
    re.compile(r"^\s*Obsoletes:\s*", re.IGNORECASE),
    re.compile(r"^\s*Obsoleted by:\s*", re.IGNORECASE),
    re.compile(r"^\s*Updates:\s*", re.IGNORECASE),
    re.compile(r"^\s*Updated by:\s*", re.IGNORECASE),
    re.compile(r"^\s*.+\[Page\s+\d+\]\s*$", re.IGNORECASE),
    re.compile(r"^\s*RFC\s+\d+\s+.+\d{4}\s*$", re.IGNORECASE),
]

TOC_DOTTED_LINE_RE = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s+.+?\.{2,}\s*\d+\s*$")
TOC_PAGED_LINE_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.?\s+)?[A-Z][A-Z0-9 /,()'\-]+\s+\d+\s*$")
SECTION_HEADER_RE = re.compile(r"^\s*(\d+(?:\.\d+)+|\d+\.)(?:\.)?[ \t]+([A-Za-z].*?)\s*$")
ICMP_ENUM_RE = re.compile(r"^\s*\d+\s*=\s+.+")
BIT_LABEL_RE = re.compile(r"^\s*\d+(?:\s+\d+)+\s*$")
ASCII_ART_RE = re.compile(r"^[|+\-]+$")
PAGE_BREAK_RE = re.compile(r"\f")
MULTI_BLANK_RE = re.compile(r"\n{3,}")
HTML_TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
TRAILING_SECTIONS = [
    re.compile(r"^\s*References\s*$", re.IGNORECASE),
    re.compile(r"^\s*Acknowledgements\s*$", re.IGNORECASE),
    re.compile(r"^\s*Author'?s Address(?:es)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*Authors'? Addresses\s*$", re.IGNORECASE),
]

EXCLUDED_DIR_NAMES = {"cleaned", "raw", "__pycache__"}


def _guess_kind(path: Path) -> str:
    name = path.name.lower()
    if name.startswith("rfc") and name.endswith(".txt"):
        return "rfc"
    return "unknown"


def _guess_protocol(path: Path, base_dir: Path) -> str:
    rel = path.relative_to(base_dir)
    return rel.parts[0] if rel.parts else "unknown"


def _guess_source_url(path: Path) -> str:
    name = path.name.lower()
    if name.startswith("rfc") and name.endswith(".txt"):
        number = name.removeprefix("rfc").split("_")[0].split(".")[0]
        if number.isdigit():
            return f"https://www.rfc-editor.org/rfc/rfc{number}.txt"
    return ""


def _html_to_text(text: str) -> str:
    text = HTML_COMMENT_RE.sub(" ", text)
    text = SCRIPT_STYLE_RE.sub(" ", text)
    text = re.sub(r"</(p|div|section|article|h1|h2|h3|h4|h5|h6|li|tr|table|ul|ol|main|header|footer|br)>", "\n", text, flags=re.IGNORECASE)
    text = HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return text


def _normalize_lines(text: str, suffix: str = "") -> list[str]:
    if suffix.lower() in {".html", ".htm"}:
        text = _html_to_text(text)

    text = PAGE_BREAK_RE.sub("\n", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if any(pattern.match(line) for pattern in SKIP_LINE_PATTERNS):
            continue
        line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(line)
    return lines


def _is_toc_line(line: str) -> bool:
    return bool(TOC_DOTTED_LINE_RE.match(line) or TOC_PAGED_LINE_RE.match(line))


def _is_section_header(line: str, protocol: str) -> bool:
    if _is_toc_line(line):
        return False
    if ICMP_ENUM_RE.match(line) or BIT_LABEL_RE.match(line):
        return False

    match = SECTION_HEADER_RE.match(line)
    if not match:
        return False

    section_id, title = match.groups()

    if protocol != "dns" and re.match(r"^\d+\.$", section_id):
        words = title.split()
        if len(words) > 4:
            return False
        if title.endswith("."):
            return False

    return True


def _has_numbered_structure(lines: list[str], protocol: str) -> bool:
    if protocol == "icmp":
        return False

    hits = 0
    for line in lines:
        if _is_section_header(line, protocol):
            hits += 1
        if hits >= 3:
            return True
    return False


def _strip_table_of_contents(lines: list[str], protocol: str) -> list[str]:
    if protocol == "dns":
        result: list[str] = []
        in_toc = False
        for line in lines:
            lower = line.lower()
            if lower == "table of contents":
                in_toc = True
                continue
            if in_toc:
                if not line:
                    continue
                if _is_toc_line(line):
                    continue
                if line == "2. INTRODUCTION":
                    in_toc = False
                    result.append(line)
                    continue
                continue
            result.append(line)
        return result

    result: list[str] = []
    in_toc = False
    toc_started = False

    for line in lines:
        lower = line.lower()
        if lower in {"table of contents", "contents"}:
            in_toc = True
            toc_started = True
            continue

        if not toc_started and _is_toc_line(line):
            in_toc = True
            toc_started = True
            continue

        if in_toc:
            if not line:
                continue
            if _is_toc_line(line):
                continue
            if _is_section_header(line, protocol):
                in_toc = False
                result.append(line)
                continue
            if re.match(r"^[A-Za-z].*", line) and not _is_toc_line(line):
                in_toc = False
                result.append(line)
                continue
            continue

        result.append(line)

    return result


def _trim_trailing_sections(lines: list[str]) -> list[str]:
    for index, line in enumerate(lines):
        plain_line = line.lstrip("# ").strip()
        if any(pattern.match(plain_line) for pattern in TRAILING_SECTIONS):
            return lines[:index]
    return lines


def _drop_front_matter(lines: list[str], numbered_mode: bool, protocol: str) -> list[str]:
    if protocol == "dns":
        for index, line in enumerate(lines):
            if line == "2. INTRODUCTION":
                return lines[index:]
        return lines

    if protocol == "icmp":
        for index, line in enumerate(lines):
            if line == "Introduction":
                return lines[index:]
        return lines

    if numbered_mode:
        start_index: int | None = None
        for index, line in enumerate(lines):
            if _is_toc_line(line):
                continue
            if not _is_section_header(line, protocol):
                continue
            match = SECTION_HEADER_RE.match(line)
            assert match is not None
            section_id = match.group(1)
            if section_id in {"1.", "2.", "1", "2"}:
                start_index = index
                break
            if start_index is None:
                start_index = index
        if start_index is None:
            return lines
        return lines[start_index:]

    for index, line in enumerate(lines):
        if not line:
            continue
        if line.lower() in {"introduction", "message formats", "overview"}:
            return lines[index:]
    return lines


def _promote_markdown_headers(lines: list[str], numbered_mode: bool, protocol: str) -> list[str]:
    promoted: list[str] = []

    for line in lines:
        if protocol == "icmp":
            if ICMP_ENUM_RE.match(line) or BIT_LABEL_RE.match(line) or ASCII_ART_RE.match(line):
                promoted.append(line)
                continue
            if re.match(r"^[A-Z][A-Za-z /\-]+Message$", line):
                promoted.append(f"# {line}")
                continue
            if line in {"Introduction", "Message Formats"}:
                promoted.append(f"# {line}")
                continue
            promoted.append(line)
            continue

        if numbered_mode:
            if not _is_section_header(line, protocol):
                promoted.append(line)
                continue

            match = SECTION_HEADER_RE.match(line)
            assert match is not None
            section_id, title = match.groups()
            normalized_section_id = section_id.rstrip(".")
            level = min(normalized_section_id.count(".") + 1, 6)
            hashes = "#" * level
            promoted.append(f"{hashes} {normalized_section_id} {title.strip()}")
            continue

        if line.isupper() and 3 <= len(line) <= 120 and not _is_toc_line(line):
            promoted.append(f"# {line.title()}")
            continue

        if re.match(r"^[A-Z][A-Za-z /\-]+Message$", line):
            promoted.append(f"# {line}")
            continue

        promoted.append(line)

    return promoted


def clean_text(text: str, suffix: str = "", protocol: str = "unknown") -> str:
    lines = _normalize_lines(text, suffix)
    numbered_mode = _has_numbered_structure(lines, protocol)
    lines = _drop_front_matter(lines, numbered_mode, protocol)
    lines = _strip_table_of_contents(lines, protocol)
    lines = _promote_markdown_headers(lines, numbered_mode, protocol)
    lines = _trim_trailing_sections(lines)

    cleaned = "\n".join(lines)
    cleaned = MULTI_BLANK_RE.sub("\n\n", cleaned)
    return cleaned.strip() + "\n"


def build_front_matter(protocol: str, kind: str, source_url: str, source_file: Path) -> str:
    return (
        f"# Source Metadata\n"
        f"- protocol: {protocol}\n"
        f"- kind: {kind}\n"
        f"- source_file: {source_file.name}\n"
        f"- source_url: {source_url or 'unknown'}\n\n"
    )


def process_file(source_file: Path, raw_base: Path, output_base: Path) -> Path:
    protocol = _guess_protocol(source_file, raw_base)
    kind = _guess_kind(source_file)
    source_url = _guess_source_url(source_file)

    text = source_file.read_text(encoding="utf-8", errors="ignore")
    cleaned_text = clean_text(text, source_file.suffix, protocol)
    result = build_front_matter(protocol, kind, source_url, source_file) + cleaned_text

    rel = source_file.relative_to(raw_base)
    target = output_base / rel.with_suffix(".md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result, encoding="utf-8")
    return target


def _iter_source_files(raw_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in raw_dir.rglob("*"):
        if not path.is_file():
            continue
        if any(part.lower() in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() not in {".txt", ".md", ".html", ".htm"}:
            continue
        files.append(path)
    return files


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="清洗 RFC 协议文档")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR, help="原始资料目录")
    parser.add_argument("--output-dir", type=Path, default=CLEAN_DIR, help="清洗输出目录")
    args = parser.parse_args()

    raw_dir = args.raw_dir
    output_dir = args.output_dir

    if not raw_dir.exists():
        raise FileNotFoundError(f"原始目录不存在: {raw_dir}")

    files = _iter_source_files(raw_dir)
    if not files:
        raise ValueError(f"原始目录下没有可处理文件: {raw_dir}")

    print("=" * 60)
    print("RFC 协议文档轻量清洗")
    print("=" * 60)
    print(f"原始目录: {raw_dir}")
    print(f"输出目录: {output_dir}")
    print(f"文件数量: {len(files)}")
    print("=" * 60)

    for file_path in files:
        target = process_file(file_path, raw_dir, output_dir)
        print(f"[OK] {file_path.relative_to(raw_dir)} -> {target.relative_to(output_dir)}")

    print("=" * 60)
    print("清洗完成!")
    print("建议后续把 DATA_DIR 指向 cleaned 目录后再执行 sync/rebuild。")
    print("=" * 60)


if __name__ == "__main__":
    main()
