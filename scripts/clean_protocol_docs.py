#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对下载后的协议资料做轻量清洗，输出更适合 RAG 的文本。"""
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
]

MULTI_BLANK_RE = re.compile(r"\n{3,}")
HTML_TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _guess_kind(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    if "tutorial" in parts:
        return "tutorial"
    if "spec" in parts:
        return "spec"
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
    if "mdn_http_overview" in name:
        return "https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview"
    if "mdn_tls_overview" in name:
        return "https://developer.mozilla.org/en-US/docs/Web/Security/Transport_Layer_Security"
    if "ipv4_companions" in name:
        return "https://intronetworks.cs.luc.edu/current2/mobile/ipv4companions.html"
    if "intronetworks_intro" in name:
        return "https://intronetworks.cs.luc.edu/current/uhtml/intro.html"
    if "intronetworks_udp" in name:
        return "https://intronetworks.cs.luc.edu/1/html/udp.html"
    return ""


def _html_to_text(text: str) -> str:
    text = HTML_COMMENT_RE.sub(" ", text)
    text = SCRIPT_STYLE_RE.sub(" ", text)
    text = re.sub(r"</(p|div|section|article|h1|h2|h3|h4|h5|h6|li|tr|table|ul|ol|main|header|footer|br)>", "\n", text, flags=re.IGNORECASE)
    text = HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return text


def clean_text(text: str, suffix: str = "") -> str:
    if suffix.lower() in {".html", ".htm"}:
        text = _html_to_text(text)

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if any(pattern.match(line) for pattern in SKIP_LINE_PATTERNS):
            continue
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
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
    cleaned_text = clean_text(text, source_file.suffix)
    result = build_front_matter(protocol, kind, source_url, source_file) + cleaned_text

    rel = source_file.relative_to(raw_base)
    target = output_base / rel.with_suffix(".md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result, encoding="utf-8")
    return target


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="清洗下载后的协议资料")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR, help="原始资料目录")
    parser.add_argument("--output-dir", type=Path, default=CLEAN_DIR, help="清洗输出目录")
    args = parser.parse_args()

    raw_dir = args.raw_dir
    output_dir = args.output_dir

    if not raw_dir.exists():
        raise FileNotFoundError(f"原始目录不存在: {raw_dir}")

    files = [path for path in raw_dir.rglob("*") if path.is_file()]
    if not files:
        raise ValueError(f"原始目录下没有可处理文件: {raw_dir}")

    print("=" * 60)
    print("协议资料轻量清洗")
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
