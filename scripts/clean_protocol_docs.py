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

RAW_DIR = Path(__file__).parent.parent / "data" / "protocols" / "raw"
CLEAN_DIR = Path(__file__).parent.parent / "data" / "protocols" / "cleaned"

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
    re.compile(r"^\s*\[page\s+\d+\]\s+.+$", re.IGNORECASE),
    re.compile(r"^\s*[A-Z][A-Za-z]+\s+\[page\s+\d+\]\s*$", re.IGNORECASE),
    re.compile(r"^\s*RFC\s+\d+\s+.+\d{4}\s*$", re.IGNORECASE),
    re.compile(r"^\s*[0-3]?\d\s+[A-Z][a-z]{2}\s+\d{4}\s*$"),
    re.compile(r"^\s*RFC\s+\d+\s+[A-Za-z][A-Za-z0-9 /.-]+$", re.IGNORECASE),
]

TOC_DOTTED_LINE_RE = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s+.+?\.{2,}\s*\d+\s*$")
TOC_PAGED_LINE_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.?\s+)?[A-Z][A-Z0-9 /,()'\-]+\s+\d+\s*$")
TOC_NUMBERED_ENTRY_RE = re.compile(r"^\s*(?:Appendix\s+[A-Z]\.\s+|\d+(?:\.\d+)*\.?)\s+.+\s*$")
SECTION_HEADER_RE = re.compile(r"^\s*((?:Appendix\s+[A-Z]\.|\d+(?:\.\d+)*\.?))(?:\.)?[ \t]+([A-Za-z].*?)\s*$")
ICMP_ENUM_RE = re.compile(r"^\s*\d+\s*=\s+.+")
BIT_LABEL_RE = re.compile(r"^\s*\d+(?:\s+\d+)+\s*$")
ASCII_ART_RE = re.compile(r"^[|+\-]+$")
UNDERLINE_HEADER_RE = re.compile(r"^-{3,}$")
PAGE_BREAK_RE = re.compile(r"\f")
MULTI_BLANK_RE = re.compile(r"\n{3,}")
HTML_TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
TRAILING_SECTIONS = [
    re.compile(r"^\s*References\s*$", re.IGNORECASE),
    re.compile(r"^\s*Acknowledgements\s*$", re.IGNORECASE),
    re.compile(r"^\s*Acknowledgments\s*$", re.IGNORECASE),
    re.compile(r"^\s*Author'?s Address(?:es)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*Authors'? Addresses\s*$", re.IGNORECASE),
]

EXCLUDED_DIR_NAMES = {"cleaned", "__pycache__"}


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
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9 /.-]+ RFC \d+", line):
            continue
        lines.append(line)
    return lines


def _looks_like_numbered_toc_entry(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.lower().startswith("table of contents"):
        return False
    if re.match(r"^(?:Appendix\s+[A-Z]\.\s+|\d+(?:\.\d+)*\.?)\s+.+$", stripped) is None:
        return False
    if stripped.endswith(":"):
        return False
    if re.match(r"^\d+\s+[A-Z][a-z]{2}\s+\d{4}$", stripped):
        return False
    return True


def _count_leading_numbered_toc_block(lines: list[str]) -> int:
    count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if count:
                break
            continue
        if _looks_like_numbered_toc_entry(stripped):
            count += 1
            continue
        if count:
            break
    return count


def _is_toc_tail_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _looks_like_numbered_toc_entry(stripped):
        return True
    return bool(
        re.match(
            r"^(?:Appendix\s+[A-Z]\.\s+.*|[A-Z]\.\d+(?:\.\d+)*\.\s+.*|Acknowledg(?:e)?ments|Author'?s Address(?:es)?|Full Copyright Statement|Index|Contributors|Resources)$",
            stripped,
            re.IGNORECASE,
        )
    )


def _is_toc_line(line: str) -> bool:
    return bool(TOC_DOTTED_LINE_RE.match(line) or TOC_PAGED_LINE_RE.match(line))


def _looks_like_numbered_toc_entry(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.lower().startswith("table of contents"):
        return False
    if re.match(r"^(?:Appendix\s+[A-Z]\.\s+|\d+(?:\.\d+)*\.?)\s+.+$", stripped) is None:
        return False
    return not stripped.endswith(":")


def _is_section_header(line: str, protocol: str) -> bool:
    if _is_toc_line(line):
        return False
    if ICMP_ENUM_RE.match(line) or BIT_LABEL_RE.match(line):
        return False

    match = SECTION_HEADER_RE.match(line)
    if not match:
        return False

    section_id, title = match.groups()
    normalized_title = title.strip()

    if protocol == "http":
        title_lower = normalized_title.lower()
        if title_lower.startswith((
            "initialize ",
            "compute ",
            "wait ",
            "if ",
            "repeat ",
            "check ",
            "close ",
            "transmit ",
        )):
            return False
        if normalized_title.endswith(":"):
            return False

    if section_id.lower().startswith("appendix"):
        return True

    if protocol != "dns" and re.match(r"^\d+\.?$", section_id):
        words = normalized_title.split()
        if len(words) > 6:
            return False
        if normalized_title.endswith("."):
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
    leading_toc_count = _count_leading_numbered_toc_block(lines)
    if leading_toc_count >= 3:
        trimmed: list[str] = []
        skipped = 0
        for line in lines:
            stripped = line.strip()
            if skipped < leading_toc_count:
                if not stripped:
                    continue
                if _looks_like_numbered_toc_entry(stripped):
                    skipped += 1
                    continue
            trimmed.append(line)
        lines = trimmed

    result: list[str] = []
    in_toc = False
    toc_started = False
    numbered_toc_hits = 0

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if lower in {"table of contents", "contents"}:
            in_toc = True
            toc_started = True
            numbered_toc_hits = 0
            continue

        if not toc_started and _is_toc_line(line):
            in_toc = True
            toc_started = True
            numbered_toc_hits = 0
            continue

        if not toc_started and _looks_like_numbered_toc_entry(stripped):
            numbered_toc_hits += 1
            if numbered_toc_hits >= 3:
                in_toc = True
                toc_started = True
                continue
        elif not toc_started and stripped:
            numbered_toc_hits = 0

        if in_toc:
            if not stripped:
                continue
            if _is_toc_line(line) or _looks_like_numbered_toc_entry(stripped):
                continue
            if _is_toc_tail_line(stripped):
                continue
            if _is_section_header(line, protocol):
                in_toc = False
                result.append(line)
                continue
            if protocol == "dns" and stripped == "2. INTRODUCTION":
                in_toc = False
                result.append(line)
                continue
            if re.match(r"^[A-Za-z].*", stripped) and not _is_toc_line(line):
                in_toc = False
                result.append(line)
                continue
            continue

        result.append(line)

    while result:
        stripped = result[0].strip()
        if _is_toc_tail_line(stripped):
            result.pop(0)
            continue
        if protocol == "dns" and not re.match(r"^(?:1\.?\s+Introduction|1\s+-\s+Terminology|1\.?\s+Terminology|2\.?\s+Introduction)$", stripped, re.IGNORECASE):
            if ". ." in stripped or re.match(r"^[A-Z]\.\d", stripped) or re.match(r"^\d+(?:\.\d+)*\.\s+.*\d+$", stripped):
                result.pop(0)
                continue
        break

    return result


def _trim_trailing_sections(lines: list[str]) -> list[str]:
    min_index = max(5, len(lines) // 5)
    for index, line in enumerate(lines):
        if index < min_index:
            continue
        plain_line = line.lstrip("# ").strip()
        if any(pattern.match(plain_line) for pattern in TRAILING_SECTIONS):
            return lines[:index]
    return lines


def _drop_front_matter(lines: list[str], numbered_mode: bool, protocol: str) -> list[str]:
    preferred_starts = []
    if protocol == "dns":
        preferred_starts = [
            "1. introduction",
            "1 introduction",
            "1 - terminology",
            "1 terminology",
            "2. introduction",
            "2 introduction",
        ]
    elif protocol == "arp":
        preferred_starts = ["notes:", "introduction"]
    elif protocol == "icmp":
        preferred_starts = ["introduction"]
    else:
        preferred_starts = [
            "1. introduction",
            "1 introduction",
            "1. purpose and scope",
            "1 purpose and scope",
            "2. introduction",
            "2 introduction",
        ]

    for index, line in enumerate(lines):
        normalized = line.strip().lower()
        if normalized in preferred_starts:
            return lines[index:]

    if numbered_mode:
        first_numbered_index: int | None = None
        for index, line in enumerate(lines):
            if _is_toc_line(line):
                continue
            if not _is_section_header(line, protocol):
                continue
            match = SECTION_HEADER_RE.match(line)
            assert match is not None
            section_id = match.group(1).rstrip(".").lower()
            if section_id in {"1", "2"}:
                return lines[index:]
            if section_id.startswith("appendix"):
                continue
            if first_numbered_index is None:
                first_numbered_index = index
        if first_numbered_index is not None:
            return lines[first_numbered_index:]
        return lines

    for index, line in enumerate(lines):
        if not line:
            continue
        if line.lower() in {"introduction", "message formats", "overview", "notes:"}:
            return lines[index:]
    return lines


def _promote_markdown_headers(lines: list[str], numbered_mode: bool, protocol: str) -> list[str]:
    promoted: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]

        if index + 1 < len(lines) and UNDERLINE_HEADER_RE.match(lines[index + 1].strip()):
            if line and not _is_toc_line(line) and not ICMP_ENUM_RE.match(line):
                level = "##" if protocol == "arp" else "#"
                promoted.append(f"{level} {line.strip()}")
                index += 2
                continue

        if promoted and line and promoted[-1] == f"# {line.strip()}":
            index += 1
            continue

        if protocol == "icmp":
            if ICMP_ENUM_RE.match(line) or BIT_LABEL_RE.match(line) or ASCII_ART_RE.match(line):
                promoted.append(line)
                index += 1
                continue
            if re.match(r"^[A-Z][A-Za-z /\-]+Message$", line):
                promoted.append(f"# {line}")
                index += 1
                continue
            if line in {"Introduction", "Message Formats"}:
                promoted.append(f"# {line}")
                index += 1
                continue
            promoted.append(line)
            index += 1
            continue

        if numbered_mode:
            if not _is_section_header(line, protocol):
                promoted.append(line)
                index += 1
                continue

            match = SECTION_HEADER_RE.match(line)
            assert match is not None
            section_id, title = match.groups()
            normalized_section_id = section_id.rstrip(".")
            normalized_title = title.strip()
            if normalized_title.isupper():
                normalized_title = normalized_title.title()
            if normalized_section_id.lower().startswith("appendix"):
                promoted.append(f"# {normalized_section_id} {normalized_title}")
                index += 1
                continue
            level = min(normalized_section_id.count(".") + 1, 6)
            hashes = "#" * level
            promoted.append(f"{hashes} {normalized_section_id} {normalized_title}")
            index += 1
            continue

        if line.isupper() and 3 <= len(line) <= 120 and not _is_toc_line(line):
            promoted.append(f"# {line.title()}")
            index += 1
            continue

        if re.match(r"^[A-Z][A-Za-z /\-]+Message$", line):
            promoted.append(f"# {line}")
            index += 1
            continue

        promoted.append(line)
        index += 1

    return promoted


def _dedupe_promoted_lines(lines: list[str]) -> list[str]:
    deduped: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if line and index + 1 < len(lines) and lines[index + 1] == f"# {line}":
            index += 1
            continue
        deduped.append(line)
        index += 1

    return deduped


def _clean_leading_noise(lines: list[str], protocol: str) -> list[str]:
    cleaned = list(lines)

    while cleaned:
        stripped = cleaned[0].strip()
        if not stripped:
            cleaned.pop(0)
            continue
        if stripped in {"Authors' Addresses", "Author's Address", "Contributors", "Index", "Resources"}:
            cleaned.pop(0)
            continue
        break

    if protocol == "dns":
        normalized: list[str] = []
        for line in cleaned:
            if "Sections # " in line:
                normalized.append(line.replace("Sections # ", "Sections ", 1))
                continue
            normalized.append(line)
        cleaned = normalized

        if cleaned:
            first = cleaned[0].strip()
            if first.startswith('The key words "MUST"'):
                cleaned.insert(0, "# 1 Terminology")
            elif first.startswith("This document introduces the Domain Name System Security Extensions"):
                cleaned.insert(0, "# 1 Introduction")
            elif first.startswith("The DNS Security Extensions (DNSSEC) introduce four new DNS resource"):
                cleaned.insert(0, "# 1 Introduction")
            elif first.startswith("The DNS Security Extensions (DNSSEC) are a collection of new resource"):
                cleaned.insert(0, "# 1 Introduction")

        return cleaned

    if cleaned and not cleaned[0].startswith("# "):
        first = cleaned[0].strip()
        if len(cleaned) > 1 and cleaned[1].startswith("## 1.1"):
            cleaned.insert(0, "# 1 Introduction")
        elif first.startswith((
            "The ",
            "This ",
            "HTTP ",
            "IP ",
            "Increasingly, ",
            "When ",
        )):
            cleaned.insert(0, "# 1 Introduction")

    return cleaned


def clean_text(text: str, suffix: str = "", protocol: str = "unknown") -> str:
    lines = _normalize_lines(text, suffix)
    numbered_mode = _has_numbered_structure(lines, protocol)
    lines = _drop_front_matter(lines, numbered_mode, protocol)
    lines = _strip_table_of_contents(lines, protocol)
    lines = _promote_markdown_headers(lines, numbered_mode, protocol)
    lines = _dedupe_promoted_lines(lines)
    lines = _trim_trailing_sections(lines)
    lines = _clean_leading_noise(lines, protocol)

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
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() not in {".txt", ".md", ".html", ".htm"}:
            continue
        files.append(path)
    files.sort(key=lambda p: str(p))
    return files


def main(raw_dir: Path = RAW_DIR, output_dir: Path = CLEAN_DIR) -> None:
    source_files = _iter_source_files(raw_dir)

    print("=" * 60)
    print("RFC 协议文档轻量清洗")
    print("=" * 60)
    print(f"原始目录: {raw_dir}")
    print(f"输出目录: {output_dir}")
    print(f"文件数量: {len(source_files)}")
    print("=" * 60)

    if not source_files:
        print("未发现待处理文件。")
        return

    for source_file in source_files:
        target = process_file(source_file, raw_dir, output_dir)
        rel_source = source_file.relative_to(raw_dir)
        rel_target = target.relative_to(output_dir)
        print(f"[OK] {rel_source} -> {rel_target}")

    print("=" * 60)
    print("清洗完成!")
    print("建议后续把 DATA_DIR 指向 cleaned 目录后再执行 sync/rebuild。")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean RFC/raw protocol documents into Markdown")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR, help=f"原始目录（默认: {RAW_DIR}）")
    parser.add_argument("--output-dir", type=Path, default=CLEAN_DIR, help=f"输出目录（默认: {CLEAN_DIR}）")
    args = parser.parse_args()

    main(args.raw_dir, args.output_dir)
