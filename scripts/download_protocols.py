#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载网络协议资料到 data/protocols/raw/ 的个人辅助脚本。

说明：
- 该脚本主要用于手动收集和补充候选资料
- 脚本内保留的来源列表可能包含历史遗留的教程型资料
- 这些来源不代表当前项目正式知识库范围
- 正式知识库方向与纳入范围以 README、docs/ 与 todo.md 为准
- 支持按资料类型或协议过滤下载
- 已存在文件默认跳过
"""
from __future__ import annotations

import io
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

try:
    import requests
except ImportError:
    print("请先安装依赖: pip install requests")
    sys.exit(1)


@dataclass(frozen=True)
class SourceItem:
    protocol: str
    kind: str
    rel_path: str
    url: str
    desc: str


SOURCES: list[SourceItem] = [
    SourceItem(
        protocol="network",
        kind="tutorial",
        rel_path="network/tutorial/intronetworks_intro.html",
        url="https://intronetworks.cs.luc.edu/current/uhtml/intro.html",
        desc="网络总体概览（An Overview of Networks）",
    ),
    SourceItem(
        protocol="tcp",
        kind="tutorial",
        rel_path="tcp/tutorial/rfc1180_tcp_ip_tutorial.txt",
        url="https://www.rfc-editor.org/rfc/rfc1180.txt",
        desc="TCP/IP 教程（RFC 1180）",
    ),
    SourceItem(
        protocol="tcp",
        kind="spec",
        rel_path="tcp/rfc793.txt",
        url="https://www.rfc-editor.org/rfc/rfc793.txt",
        desc="TCP 规范（RFC 793）",
    ),
    SourceItem(
        protocol="tcp",
        kind="spec",
        rel_path="tcp/rfc9293.txt",
        url="https://www.rfc-editor.org/rfc/rfc9293.txt",
        desc="TCP 规范（RFC 9293）",
    ),
    SourceItem(
        protocol="udp",
        kind="tutorial",
        rel_path="udp/tutorial/intronetworks_udp.html",
        url="https://intronetworks.cs.luc.edu/1/html/udp.html",
        desc="UDP 教程（Intronetworks）",
    ),
    SourceItem(
        protocol="udp",
        kind="spec",
        rel_path="udp/rfc768.txt",
        url="https://www.rfc-editor.org/rfc/rfc768.txt",
        desc="UDP 规范（RFC 768）",
    ),
    SourceItem(
        protocol="http",
        kind="tutorial",
        rel_path="http/tutorial/mdn_http_overview.html",
        url="https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview",
        desc="HTTP 概览（MDN）",
    ),
    SourceItem(
        protocol="http",
        kind="spec",
        rel_path="http/rfc2616.txt",
        url="https://www.rfc-editor.org/rfc/rfc2616.txt",
        desc="HTTP/1.1 规范（RFC 2616）",
    ),
    SourceItem(
        protocol="http",
        kind="spec",
        rel_path="http/rfc2818.txt",
        url="https://www.rfc-editor.org/rfc/rfc2818.txt",
        desc="HTTP Over TLS（RFC 2818）",
    ),
    SourceItem(
        protocol="http",
        kind="spec",
        rel_path="http/rfc7540.txt",
        url="https://www.rfc-editor.org/rfc/rfc7540.txt",
        desc="HTTP/2 规范（RFC 7540）",
    ),
    SourceItem(
        protocol="http",
        kind="spec",
        rel_path="http/rfc9110.txt",
        url="https://www.rfc-editor.org/rfc/rfc9110.txt",
        desc="HTTP Semantics（RFC 9110）",
    ),
    SourceItem(
        protocol="http",
        kind="spec",
        rel_path="http/rfc9112.txt",
        url="https://www.rfc-editor.org/rfc/rfc9112.txt",
        desc="HTTP/1.1（RFC 9112）",
    ),
    SourceItem(
        protocol="http",
        kind="spec",
        rel_path="http/rfc9113.txt",
        url="https://www.rfc-editor.org/rfc/rfc9113.txt",
        desc="HTTP/2（RFC 9113）",
    ),
    SourceItem(
        protocol="http",
        kind="spec",
        rel_path="http/rfc9114.txt",
        url="https://www.rfc-editor.org/rfc/rfc9114.txt",
        desc="HTTP/3（RFC 9114）",
    ),
    SourceItem(
        protocol="dns",
        kind="tutorial",
        rel_path="dns/tutorial/intronetworks_ipv4_companions.html",
        url="https://intronetworks.cs.luc.edu/current2/mobile/ipv4companions.html",
        desc="IPv4 伴随协议（含 DNS/ARP/ICMP）",
    ),
    SourceItem(
        protocol="dns",
        kind="spec",
        rel_path="dns/rfc1034.txt",
        url="https://www.rfc-editor.org/rfc/rfc1034.txt",
        desc="DNS 概念（RFC 1034）",
    ),
    SourceItem(
        protocol="dns",
        kind="spec",
        rel_path="dns/rfc1035.txt",
        url="https://www.rfc-editor.org/rfc/rfc1035.txt",
        desc="DNS 规范（RFC 1035）",
    ),
    SourceItem(
        protocol="dns",
        kind="spec",
        rel_path="dns/rfc2308.txt",
        url="https://www.rfc-editor.org/rfc/rfc2308.txt",
        desc="DNS Negative Caching（RFC 2308）",
    ),
    SourceItem(
        protocol="dns",
        kind="spec",
        rel_path="dns/rfc4033.txt",
        url="https://www.rfc-editor.org/rfc/rfc4033.txt",
        desc="DNSSEC Introduction（RFC 4033）",
    ),
    SourceItem(
        protocol="dns",
        kind="spec",
        rel_path="dns/rfc4034.txt",
        url="https://www.rfc-editor.org/rfc/rfc4034.txt",
        desc="DNSSEC Resource Records（RFC 4034）",
    ),
    SourceItem(
        protocol="dns",
        kind="spec",
        rel_path="dns/rfc4035.txt",
        url="https://www.rfc-editor.org/rfc/rfc4035.txt",
        desc="DNSSEC Protocol Modifications（RFC 4035）",
    ),
    SourceItem(
        protocol="tls",
        kind="tutorial",
        rel_path="tls/tutorial/mdn_tls_overview.html",
        url="https://developer.mozilla.org/en-US/docs/Web/Security/Transport_Layer_Security",
        desc="TLS 概览（MDN）",
    ),
    SourceItem(
        protocol="tls",
        kind="spec",
        rel_path="tls/rfc5246.txt",
        url="https://www.rfc-editor.org/rfc/rfc5246.txt",
        desc="TLS 1.2 规范（RFC 5246）",
    ),
    SourceItem(
        protocol="tls",
        kind="spec",
        rel_path="tls/rfc6066.txt",
        url="https://www.rfc-editor.org/rfc/rfc6066.txt",
        desc="TLS Extensions（RFC 6066）",
    ),
    SourceItem(
        protocol="tls",
        kind="spec",
        rel_path="tls/rfc7301.txt",
        url="https://www.rfc-editor.org/rfc/rfc7301.txt",
        desc="ALPN（RFC 7301）",
    ),
    SourceItem(
        protocol="tls",
        kind="spec",
        rel_path="tls/rfc8446.txt",
        url="https://www.rfc-editor.org/rfc/rfc8446.txt",
        desc="TLS 1.3 规范（RFC 8446）",
    ),
    SourceItem(
        protocol="tls",
        kind="spec",
        rel_path="tls/rfc5280.txt",
        url="https://www.rfc-editor.org/rfc/rfc5280.txt",
        desc="X.509 PKI Certificate Profile（RFC 5280）",
    ),
    SourceItem(
        protocol="ip",
        kind="tutorial",
        rel_path="ip/tutorial/intronetworks_intro.html",
        url="https://intronetworks.cs.luc.edu/current/uhtml/intro.html",
        desc="IP/网络层概览（Intronetworks）",
    ),
    SourceItem(
        protocol="ip",
        kind="spec",
        rel_path="ip/rfc791.txt",
        url="https://www.rfc-editor.org/rfc/rfc791.txt",
        desc="IP 规范（RFC 791）",
    ),
    SourceItem(
        protocol="ip",
        kind="spec",
        rel_path="ip/rfc8200.txt",
        url="https://www.rfc-editor.org/rfc/rfc8200.txt",
        desc="IPv6 Specification（RFC 8200）",
    ),
    SourceItem(
        protocol="ip",
        kind="spec",
        rel_path="ip/rfc8201.txt",
        url="https://www.rfc-editor.org/rfc/rfc8201.txt",
        desc="IPv6 Path MTU Discovery（RFC 8201）",
    ),
    SourceItem(
        protocol="ip",
        kind="spec",
        rel_path="ip/rfc1122.txt",
        url="https://www.rfc-editor.org/rfc/rfc1122.txt",
        desc="Host Requirements（RFC 1122）",
    ),
    SourceItem(
        protocol="arp",
        kind="tutorial",
        rel_path="arp/tutorial/intronetworks_ipv4_companions.html",
        url="https://intronetworks.cs.luc.edu/current2/mobile/ipv4companions.html",
        desc="ARP 教程（Intronetworks）",
    ),
    SourceItem(
        protocol="arp",
        kind="spec",
        rel_path="arp/rfc826.txt",
        url="https://www.rfc-editor.org/rfc/rfc826.txt",
        desc="ARP 规范（RFC 826）",
    ),
    SourceItem(
        protocol="icmp",
        kind="spec",
        rel_path="icmp/rfc792.txt",
        url="https://www.rfc-editor.org/rfc/rfc792.txt",
        desc="ICMP 规范（RFC 792）",
    ),
]

DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data" / "protocols" / "raw"
TIMEOUT = 30
USER_AGENT = "cc-test-rag-demo/1.0"


def _normalize_csv(value: str) -> set[str]:
    return {part.strip().lower() for part in value.split(",") if part.strip()}


def _select_sources(kind: str, protocols: str | None) -> list[SourceItem]:
    selected = SOURCES
    kind = kind.lower()
    if kind != "all":
        selected = [item for item in selected if item.kind == kind]

    if protocols:
        wanted = _normalize_csv(protocols)
        selected = [item for item in selected if item.protocol in wanted]

    return selected


def download_file(item: SourceItem, target: Path) -> bool:
    print(f"正在下载: {item.desc}")
    print(f"  kind={item.kind} protocol={item.protocol}")
    print(f"  URL: {item.url}")

    try:
        response = requests.get(
            item.url,
            timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)

        size = target.stat().st_size
        print(f"  [OK] 已保存: {target.relative_to(target.parents[2])} ({size:,} bytes)")
        return True
    except requests.exceptions.HTTPError as exc:
        print(f"  [X] HTTP 错误: {exc}")
    except requests.exceptions.ConnectionError as exc:
        print(f"  [X] 连接错误: {exc}")
    except requests.exceptions.Timeout as exc:
        print(f"  [X] 超时: {exc}")
    except Exception as exc:
        print(f"  [X] 错误: {exc}")
    return False


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="下载精选网络协议资料")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"下载目录（默认: {DEFAULT_DATA_DIR}）",
    )
    parser.add_argument(
        "--kind",
        choices=["tutorial", "spec", "all"],
        default="all",
        help="按资料类型过滤下载",
    )
    parser.add_argument(
        "--protocol",
        type=str,
        help="按协议过滤，逗号分隔，例如 tcp,http,dns",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新下载已存在文件",
    )
    args = parser.parse_args()

    sources = _select_sources(args.kind, args.protocol)
    data_dir = args.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("精选网络协议资料下载器")
    print("=" * 60)
    print(f"目标目录: {data_dir}")
    print(f"资料数量: {len(sources)}")
    print(f"资料类型: {args.kind}")
    print(f"协议过滤: {args.protocol or '全部'}")
    print("=" * 60)

    success = 0
    skipped = 0
    failed = 0
    by_kind: dict[str, int] = defaultdict(int)
    start_time = datetime.now()

    for item in sources:
        target = data_dir / item.rel_path
        if target.exists() and not args.force:
            print(f"[SKIP] 跳过 (已存在): {item.desc}")
            skipped += 1
            by_kind[item.kind] += 1
            continue

        if download_file(item, target):
            success += 1
            by_kind[item.kind] += 1
        else:
            failed += 1

    elapsed = (datetime.now() - start_time).total_seconds()

    print("=" * 60)
    print("下载完成!")
    print(f"  成功: {success}")
    print(f"  跳过: {skipped}")
    print(f"  失败: {failed}")
    print(f"  教程型: {by_kind.get('tutorial', 0)}")
    print(f"  规范型: {by_kind.get('spec', 0)}")
    print(f"  耗时: {elapsed:.1f} 秒")
    print("=" * 60)

    files = [f for f in data_dir.rglob("*") if f.is_file()]
    if files:
        total_size = sum(f.stat().st_size for f in files)
        print(f"\n当前目录共有 {len(files)} 个文件，总计 {total_size:,} bytes:")
        for file_path in sorted(files):
            size = file_path.stat().st_size
            print(f"  - {file_path.relative_to(data_dir)} ({size:,} bytes)")


if __name__ == "__main__":
    main()
