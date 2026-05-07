"""自动评分脚本：根据 results.csv 生成 manual_scoring_draft.csv"""

import csv
import json
import os
import sys
import re

EVAL_DIR = "runs/eval"


def load_results(run_dir):
    path = os.path.join(EVAL_DIR, run_dir, "results.csv")
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_contexts(contexts_str):
    """Parse the JSON-like contexts string into a list of text chunks."""
    try:
        ctxs = json.loads(contexts_str)
        if isinstance(ctxs, list):
            return ctxs
    except (json.JSONDecodeError, TypeError):
        pass
    return [contexts_str] if contexts_str else []


def extract_source_files(contexts):
    """Extract source file names from context metadata blocks."""
    sources = set()
    for ctx in contexts:
        match = re.search(r"source_file:\s*(\S+)", ctx)
        if match:
            sources.add(match.group(1))
    return sources


def score_retrieval_relevance(row):
    """Score based on whether target document was hit and source diversity."""
    target_hit = row.get("target_hit", "").strip() == "True"
    unique_sources = int(row.get("unique_source_count", 0) or 0)
    contexts_count = int(row.get("contexts_count", 0) or 0)

    if target_hit and contexts_count >= 2:
        return 2
    elif target_hit or contexts_count >= 2:
        return 1
    else:
        return 0


def score_faithfulness(row):
    """Score whether answer is grounded in retrieved context."""
    refused = row.get("refused", "").strip() == "True"
    answer = row.get("answer", "")
    contexts_str = row.get("contexts", "")
    contexts = parse_contexts(contexts_str)
    contexts_count = int(row.get("contexts_count", 0) or 0)

    if refused:
        return 2 if "资料不足以确定" in answer else 1

    if not contexts or contexts_count == 0:
        return 0

    # Check for technical terms (English) from contexts appearing in answer
    # RFC contexts are in English, answers in Chinese but cite English terms
    context_text = " ".join(contexts)
    # Extract English technical terms (acronyms, protocol names, etc.)
    ctx_terms = set(re.findall(r'\b[A-Z][A-Z0-9/]{1,}\b', context_text))
    ans_terms = set(re.findall(r'\b[A-Z][A-Z0-9/]{1,}\b', answer))

    if ctx_terms and ans_terms:
        overlap = len(ans_terms & ctx_terms) / len(ans_terms)
        if overlap >= 0.3:
            return 2
        elif overlap >= 0.1:
            return 1
        else:
            return 0
    else:
        # No English terms to compare; fall back to length heuristic
        return 1 if len(answer) > 50 else 0


def score_correctness(row):
    """Score technical correctness based on answer patterns."""
    refused = row.get("refused", "").strip() == "True"
    answer = row.get("answer", "")

    if refused:
        # Refusal is correct behavior for refusal questions
        should_refuse = row.get("should_refuse", "").strip() == "True"
        if should_refuse and "资料不足以确定" in answer:
            return 2
        elif should_refuse:
            return 1
        else:
            return 0

    # Check for obvious issues
    if not answer or len(answer) < 20:
        return 0

    # If answer has structured sections, it's likely well-formed
    has_sections = bool(re.search(r'#{1,3}\s|^\d+\.', answer, re.MULTILINE))
    has_detail = len(answer) > 100

    if has_sections and has_detail:
        return 2
    elif has_detail:
        return 1
    else:
        return 0


def score_completeness(row):
    """Score answer completeness."""
    refused = row.get("refused", "").strip() == "True"
    answer = row.get("answer", "")

    if refused:
        return 0

    answer_len = len(answer)
    # Check for multiple sections/points
    section_count = len(re.findall(r'#{1,3}\s|^\d+\.\s', answer, re.MULTILINE))
    bullet_count = len(re.findall(r'^[-*]\s', answer, re.MULTILINE))

    if answer_len > 300 and (section_count >= 3 or bullet_count >= 3):
        return 2
    elif answer_len > 100:
        return 1
    else:
        return 0


def generate_notes(row):
    """Generate automatic notes for notable cases."""
    notes = []
    refused = row.get("refused", "").strip() == "True"
    should_refuse = row.get("should_refuse", "").strip() == "True"
    target_hit = row.get("target_hit", "").strip() == "True"

    if refused and not should_refuse:
        notes.append("非拒答题但出现保守回答")
    elif not refused and should_refuse:
        notes.append("应保守回答但系统未保守回答")
    if not target_hit and not refused:
        notes.append("目标文档未命中")

    return "，".join(notes)


def score_row(row):
    correctness = score_correctness(row)
    completeness = score_completeness(row)
    faithfulness = score_faithfulness(row)
    relevance = score_retrieval_relevance(row)
    notes = generate_notes(row)

    return {
        "correctness_score": correctness,
        "completeness_score": completeness,
        "faithfulness_score": faithfulness,
        "retrieval_relevance_score": relevance,
        "manual_notes": notes,
    }


def write_draft(run_dir, results_rows, scored_rows):
    out_path = os.path.join(EVAL_DIR, run_dir, "manual_scoring_draft.csv")
    fieldnames = [
        "id", "question", "protocol_group", "question_type",
        "target_document", "difficulty", "should_refuse", "section",
        "correctness_score", "completeness_score", "faithfulness_score",
        "retrieval_relevance_score", "manual_notes",
    ]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r, s in zip(results_rows, scored_rows):
            writer.writerow({
                "id": r["id"],
                "question": r["question"],
                "protocol_group": r["protocol_group"],
                "question_type": r["question_type"],
                "target_document": r["target_document"],
                "difficulty": r["difficulty"],
                "should_refuse": r["should_refuse"],
                "section": r["section"],
                **s,
            })
    return out_path


def print_summary(run_dir, scored_rows):
    n = len(scored_rows)
    avg_c = sum(s["correctness_score"] for s in scored_rows) / n
    avg_cm = sum(s["completeness_score"] for s in scored_rows) / n
    avg_f = sum(s["faithfulness_score"] for s in scored_rows) / n
    avg_r = sum(s["retrieval_relevance_score"] for s in scored_rows) / n
    print(f"\n=== {run_dir} ===")
    print(f"  正确性: {avg_c:.2f}")
    print(f"  完整性: {avg_cm:.2f}")
    print(f"  忠实度: {avg_f:.2f}")
    print(f"  检索相关性: {avg_r:.2f}")

    # Flag cases needing review
    need_review = [s for s in scored_rows if s["manual_notes"]]
    if need_review:
        print(f"  需复核: {len(need_review)} 题")


if __name__ == "__main__":
    runs = sys.argv[1:] if len(sys.argv) > 1 else [
        "20260507_094531_prompt_v1",
        "20260430_230707_with_rewrite",
    ]

    for run_dir in runs:
        results = load_results(run_dir)
        scored = [score_row(r) for r in results]
        out = write_draft(run_dir, results, scored)
        print_summary(run_dir, scored)
        print(f"  已生成: {out}")
