from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from src.ingest import build_index

ProgressCallback = Callable[[str, float | None], None]


def run_ingest(
    mode: str,
    chunk_strategy: str,
    progress_callback: ProgressCallback | None = None,
) -> tuple[dict[str, Any] | None, list[str], str | None]:
    runtime_logs: list[str] = []

    def report(message: str, progress: float | None = None) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        runtime_logs.append(f"[{timestamp}] {message}")
        if progress_callback:
            progress_callback(message, progress)

    try:
        report("开始执行向量库构建...", 0.01)
        stats = build_index(
            mode=mode,
            chunk_strategy=chunk_strategy,
            progress_callback=report,
        )
    except Exception as exc:
        report("向量库构建失败。", 1.0)
        return None, runtime_logs, str(exc)

    report("向量库构建完成。", 1.0)
    return stats, runtime_logs, None
