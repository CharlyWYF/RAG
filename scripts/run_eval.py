from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.qa_service import execute_qa_flow


DEFAULT_QUESTION_SET = PROJECT_ROOT / "docs" / "test_question_set" / "test_question_set.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "runs" / "eval"


def load_questions(question_set_path: Path) -> list[dict[str, Any]]:
    return json.loads(question_set_path.read_text(encoding="utf-8"))


def normalize_target_document(target_document: str) -> list[str]:
    parts = [part.strip() for part in target_document.split("/")]
    return [part for part in parts if part]


def compute_source_metrics(sources: list[str], target_document: str) -> dict[str, Any]:
    unique_sources = list(dict.fromkeys(str(src) for src in sources))
    target_tokens = normalize_target_document(target_document)
    matched_targets = [
        token for token in target_tokens
        if any(token.lower().replace(" ", "") in src.lower().replace(" ", "") for src in unique_sources)
    ]
    return {
        "source_count": len(sources),
        "unique_source_count": len(unique_sources),
        "matched_target_documents": matched_targets,
        "target_hit": bool(matched_targets),
        "unique_sources": unique_sources,
    }


def extract_timing_value(timings: list[dict[str, Any]], stage: str) -> float:
    for item in timings:
        if str(item.get("stage", "")) == stage:
            return float(item.get("seconds", 0.0))
    return 0.0


def run_single_question(
    item: dict[str, Any],
    verbose: bool = True,
) -> dict[str, Any]:
    if verbose:
        print(f"  ├─ 协议类别: {item['protocol_group']} | 题型: {item['question_type']} | 目标: {item['target_document']}")
        print(f"  ├─ 难度: {item['difficulty']} | 应保守回答: {item['should_refuse']}")
        print("  ├─ 开始执行 execute_qa_flow...")

    result = execute_qa_flow(str(item["question"]))
    timings = result.get("timings", [])
    sources = [str(src) for src in result.get("sources", [])]
    source_metrics = compute_source_metrics(sources, str(item.get("target_document", "")))

    answer = str(result.get("answer", ""))
    should_refuse = bool(item.get("should_refuse", False))
    refusal_phrase = "资料不足以确定"
    refused = refusal_phrase in answer

    row = {
        "id": item["id"],
        "question": item["question"],
        "protocol_group": item["protocol_group"],
        "question_type": item["question_type"],
        "target_document": item["target_document"],
        "difficulty": item["difficulty"],
        "expected_keypoints": item["expected_keypoints"],
        "should_refuse": should_refuse,
        "section": item["section"],
        "answer": answer,
        "rewritten_queries": result.get("rewritten_queries", []),
        "timings": timings,
        "total_seconds": float(result.get("total_seconds", 0.0)),
        "first_token_seconds": extract_timing_value(timings, "first_token"),
        "load_settings_seconds": extract_timing_value(timings, "load_settings"),
        "init_retriever_seconds": extract_timing_value(timings, "init_retriever"),
        "retrieve_seconds": extract_timing_value(timings, "retrieve"),
        "init_llm_seconds": extract_timing_value(timings, "init_llm"),
        "rewrite_seconds": extract_timing_value(timings, "rewrite_query"),
        "generate_answer_seconds": extract_timing_value(timings, "generate_answer"),
        "source_count": source_metrics["source_count"],
        "unique_source_count": source_metrics["unique_source_count"],
        "target_hit": source_metrics["target_hit"],
        "matched_target_documents": source_metrics["matched_target_documents"],
        "unique_sources": source_metrics["unique_sources"],
        "contexts": result.get("contexts", []),
        "logs": result.get("logs", []),
        "refused": refused,
        "refusal_expected_and_triggered": should_refuse and refused,
    }

    if verbose:
        print(f"  ├─ 查询改写: {row['rewritten_queries']}")
        print(
            f"  ├─ 耗时: total={row['total_seconds']:.3f}s | first_token={row['first_token_seconds']:.3f}s | "
            f"rewrite={row['rewrite_seconds']:.3f}s | retrieve={row['retrieve_seconds']:.3f}s | "
            f"generate={row['generate_answer_seconds']:.3f}s"
        )
        print(
            f"  ├─ 来源: total={row['source_count']} | unique={row['unique_source_count']} | "
            f"target_hit={row['target_hit']} | matched={row['matched_target_documents']}"
        )
        print(f"  ├─ 是否拒答: {row['refused']} | 拒答符合预期: {row['refusal_expected_and_triggered']}")
        preview = answer.replace("\n", " ")[:120]
        print(f"  └─ 回答预览: {preview}{'...' if len(answer) > 120 else ''}")

    return row


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "id",
        "question",
        "protocol_group",
        "question_type",
        "target_document",
        "difficulty",
        "expected_keypoints",
        "should_refuse",
        "section",
        "target_hit",
        "refused",
        "refusal_expected_and_triggered",
        "total_seconds",
        "first_token_seconds",
        "rewrite_seconds",
        "retrieve_seconds",
        "generate_answer_seconds",
        "source_count",
        "unique_source_count",
        "matched_target_documents",
        "rewritten_queries",
        "unique_sources",
        "timings",
        "logs",
        "contexts_count",
        "contexts",
        "answer",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "id": row["id"],
                "question": row["question"],
                "protocol_group": row["protocol_group"],
                "question_type": row["question_type"],
                "target_document": row["target_document"],
                "difficulty": row["difficulty"],
                "expected_keypoints": row["expected_keypoints"],
                "should_refuse": row["should_refuse"],
                "section": row["section"],
                "target_hit": row["target_hit"],
                "refused": row["refused"],
                "refusal_expected_and_triggered": row["refusal_expected_and_triggered"],
                "total_seconds": row["total_seconds"],
                "first_token_seconds": row["first_token_seconds"],
                "rewrite_seconds": row["rewrite_seconds"],
                "retrieve_seconds": row["retrieve_seconds"],
                "generate_answer_seconds": row["generate_answer_seconds"],
                "source_count": row["source_count"],
                "unique_source_count": row["unique_source_count"],
                "matched_target_documents": json.dumps(row.get("matched_target_documents", []), ensure_ascii=False),
                "rewritten_queries": json.dumps(row.get("rewritten_queries", []), ensure_ascii=False),
                "unique_sources": json.dumps(row.get("unique_sources", []), ensure_ascii=False),
                "timings": json.dumps(row.get("timings", []), ensure_ascii=False),
                "logs": json.dumps(row.get("logs", []), ensure_ascii=False),
                "contexts_count": len(row.get("contexts", [])),
                "contexts": json.dumps(row.get("contexts", []), ensure_ascii=False),
                "answer": row["answer"],
            })


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    if total == 0:
        return {"total_questions": 0}

    protocol_counter = Counter(row["protocol_group"] for row in rows)
    type_counter = Counter(row["question_type"] for row in rows)
    section_counter = Counter(row["section"] for row in rows)

    avg_total_seconds = sum(float(row["total_seconds"]) for row in rows) / total
    avg_first_token_seconds = sum(float(row["first_token_seconds"]) for row in rows) / total
    avg_load_settings_seconds = sum(float(row.get("load_settings_seconds", 0.0)) for row in rows) / total
    avg_init_retriever_seconds = sum(float(row.get("init_retriever_seconds", 0.0)) for row in rows) / total
    avg_rewrite_seconds = sum(float(row["rewrite_seconds"]) for row in rows) / total
    avg_retrieve_seconds = sum(float(row["retrieve_seconds"]) for row in rows) / total
    avg_init_llm_seconds = sum(float(row.get("init_llm_seconds", 0.0)) for row in rows) / total
    avg_generate_answer_seconds = sum(float(row["generate_answer_seconds"]) for row in rows) / total
    avg_unique_source_count = sum(int(row["unique_source_count"]) for row in rows) / total
    target_hit_count = sum(1 for row in rows if row["target_hit"])
    refusal_expected_count = sum(1 for row in rows if row["should_refuse"])
    refusal_triggered_count = sum(1 for row in rows if row["refusal_expected_and_triggered"])

    by_protocol: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["protocol_group"]].append(row)

    for protocol, items in grouped.items():
        count = len(items)
        by_protocol[protocol] = {
            "count": count,
            "avg_total_seconds": sum(float(item["total_seconds"]) for item in items) / count,
            "avg_first_token_seconds": sum(float(item["first_token_seconds"]) for item in items) / count,
            "avg_unique_source_count": sum(int(item["unique_source_count"]) for item in items) / count,
            "target_hit_rate": sum(1 for item in items if item["target_hit"]) / count,
        }

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_questions": total,
        "protocol_distribution": dict(protocol_counter),
        "question_type_distribution": dict(type_counter),
        "section_distribution": dict(section_counter),
        "avg_total_seconds": avg_total_seconds,
        "avg_first_token_seconds": avg_first_token_seconds,
        "avg_load_settings_seconds": avg_load_settings_seconds,
        "avg_init_retriever_seconds": avg_init_retriever_seconds,
        "avg_rewrite_seconds": avg_rewrite_seconds,
        "avg_retrieve_seconds": avg_retrieve_seconds,
        "avg_init_llm_seconds": avg_init_llm_seconds,
        "avg_generate_answer_seconds": avg_generate_answer_seconds,
        "avg_unique_source_count": avg_unique_source_count,
        "target_hit_count": target_hit_count,
        "target_hit_rate": target_hit_count / total,
        "refusal_expected_count": refusal_expected_count,
        "refusal_triggered_count": refusal_triggered_count,
        "refusal_success_rate": (refusal_triggered_count / refusal_expected_count) if refusal_expected_count else 0.0,
        "by_protocol": by_protocol,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run automated QA evaluation over the structured question set")
    parser.add_argument("--question-set", type=Path, default=DEFAULT_QUESTION_SET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    questions = load_questions(args.question_set)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.output_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] 题集文件: {args.question_set}")
    print(f"[INFO] 输出目录: {run_dir}")
    print(f"[INFO] 共 {len(questions)} 道题，开始执行...\n")

    results: list[dict[str, Any]] = []
    total_questions = len(questions)
    for index, item in enumerate(questions, start=1):
        print(f"[RUN {index}/{total_questions}] Q{item['id']}: {item['question']}")
        row = run_single_question(item, verbose=True)
        results.append(row)
        print()

    print("[INFO] 正在汇总统计信息...")
    summary = build_summary(results)

    print("[INFO] 正在写出 results.jsonl / results.csv / summary.json ...")
    write_jsonl(run_dir / "results.jsonl", results)
    write_csv(run_dir / "results.csv", results)
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n[OK] 评测完成")
    print(f"输出目录: {run_dir}")
    print(f"题目数量: {summary['total_questions']}")
    print(f"平均总耗时: {summary['avg_total_seconds']:.3f}s")
    print(f"平均首字时间: {summary['avg_first_token_seconds']:.3f}s")
    print(f"目标文档命中率: {summary['target_hit_rate']:.3f}")


if __name__ == "__main__":
    main()
