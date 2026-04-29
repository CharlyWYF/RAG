from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCORING = PROJECT_ROOT / "runs" / "eval" / "20260429_173324" / "manual_scoring_draft.csv"


def load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_float(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    protocol_counter = Counter(row["protocol_group"] for row in rows)
    type_counter = Counter(row["question_type"] for row in rows)
    section_counter = Counter(row["section"] for row in rows)

    avg_correctness = sum(to_float(row["correctness_score"]) for row in rows) / total if total else 0.0
    avg_completeness = sum(to_float(row["completeness_score"]) for row in rows) / total if total else 0.0
    avg_faithfulness = sum(to_float(row["faithfulness_score"]) for row in rows) / total if total else 0.0
    avg_retrieval_relevance = sum(to_float(row["retrieval_relevance_score"]) for row in rows) / total if total else 0.0

    by_protocol: dict[str, dict[str, Any]] = {}
    grouped_protocol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped_protocol[row["protocol_group"]].append(row)

    for protocol, items in grouped_protocol.items():
        count = len(items)
        by_protocol[protocol] = {
            "count": count,
            "avg_correctness": sum(to_float(item["correctness_score"]) for item in items) / count,
            "avg_completeness": sum(to_float(item["completeness_score"]) for item in items) / count,
            "avg_faithfulness": sum(to_float(item["faithfulness_score"]) for item in items) / count,
            "avg_retrieval_relevance": sum(to_float(item["retrieval_relevance_score"]) for item in items) / count,
        }

    by_question_type: dict[str, dict[str, Any]] = {}
    grouped_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped_type[row["question_type"]].append(row)

    for qtype, items in grouped_type.items():
        count = len(items)
        by_question_type[qtype] = {
            "count": count,
            "avg_correctness": sum(to_float(item["correctness_score"]) for item in items) / count,
            "avg_completeness": sum(to_float(item["completeness_score"]) for item in items) / count,
            "avg_faithfulness": sum(to_float(item["faithfulness_score"]) for item in items) / count,
            "avg_retrieval_relevance": sum(to_float(item["retrieval_relevance_score"]) for item in items) / count,
        }

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_questions": total,
        "protocol_distribution": dict(protocol_counter),
        "question_type_distribution": dict(type_counter),
        "section_distribution": dict(section_counter),
        "avg_correctness": avg_correctness,
        "avg_completeness": avg_completeness,
        "avg_faithfulness": avg_faithfulness,
        "avg_retrieval_relevance": avg_retrieval_relevance,
        "by_protocol": by_protocol,
        "by_question_type": by_question_type,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze manual scoring draft CSV")
    parser.add_argument("--scoring", type=Path, default=DEFAULT_SCORING)
    args = parser.parse_args()

    rows = load_rows(args.scoring)
    summary = summarize(rows)
    out_path = args.scoring.with_name("manual_scoring_summary.json")
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] 已生成: {out_path}")
    print(f"题目总数: {summary['total_questions']}")
    print(f"平均正确性: {summary['avg_correctness']:.3f}")
    print(f"平均完整性: {summary['avg_completeness']:.3f}")
    print(f"平均忠实性: {summary['avg_faithfulness']:.3f}")
    print(f"平均检索相关性: {summary['avg_retrieval_relevance']:.3f}")


if __name__ == "__main__":
    main()
