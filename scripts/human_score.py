"""人工评分脚本：逐题评估并生成最终 manual_scoring_draft.csv"""

import csv
import json
import os
import re
import sys

EVAL_DIR = "runs/eval"


def load_results(run_dir):
    path = os.path.join(EVAL_DIR, run_dir, "results.csv")
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_contexts(contexts_str):
    try:
        ctxs = json.loads(contexts_str)
        return ctxs if isinstance(ctxs, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def extract_english_terms(text):
    """Extract English technical terms from text."""
    return set(re.findall(r'\b[A-Z][A-Z0-9/._-]{1,}\b', text))


def has_rfc_reference(answer):
    """Check if answer references specific RFCs."""
    return bool(re.search(r'RFC\s*\d+', answer))


def count_answer_points(answer):
    """Count structured points in answer."""
    bullets = len(re.findall(r'^\s*[-*]\s', answer, re.MULTILINE))
    numbered = len(re.findall(r'^\s*\d+[.)]\s', answer, re.MULTILINE))
    headers = len(re.findall(r'^#{1,3}\s', answer, re.MULTILINE))
    return max(bullets, numbered, headers)


def score_single(row):
    """Score a single question based on all available information."""
    qid = row["id"]
    question = row["question"]
    answer = row.get("answer", "")
    refused = row.get("refused", "").strip() == "True"
    should_refuse = row.get("should_refuse", "").strip() == "True"
    target_hit = row.get("target_hit", "").strip() == "True"
    question_type = row.get("question_type", "")
    contexts_str = row.get("contexts", "")
    contexts = parse_contexts(contexts_str)
    unique_sources = int(row.get("unique_source_count", 0) or 0)
    contexts_count = int(row.get("contexts_count", 0) or 0)

    notes = []

    # ===== 拒答题 =====
    if refused:
        faithfulness = 2  # 拒答本身就是忠实的
        retrieval_relevance = 1 if contexts_count > 0 else 0

        if should_refuse:
            # 正确拒答
            correctness = 2
            completeness = 0
            if "资料不足以确定" not in answer:
                notes.append("拒答但措辞异常")
        else:
            # 误拒答
            correctness = 0
            completeness = 0
            notes.append("非拒答题但出现保守回答")
            if not target_hit:
                notes.append("目标文档未命中")

        return {
            "correctness_score": correctness,
            "completeness_score": completeness,
            "faithfulness_score": faithfulness,
            "retrieval_relevance_score": retrieval_relevance,
            "manual_notes": "，".join(notes),
        }

    # ===== 该拒却没拒 =====
    if should_refuse and not refused:
        notes.append("应保守回答但系统未保守回答")
        # 系统给了详细回答，评估回答本身的质量
        correctness = 1  # 降级，因为本应拒答
        completeness = score_completeness_heuristic(answer)
        faithfulness = score_faithfulness_heuristic(answer, contexts)
        relevance = 2 if target_hit else (1 if contexts_count >= 2 else 0)

        return {
            "correctness_score": correctness,
            "completeness_score": completeness,
            "faithfulness_score": faithfulness,
            "retrieval_relevance_score": relevance,
            "manual_notes": "，".join(notes),
        }

    # ===== 正常回答 =====
    # Correctness
    if not answer or len(answer) < 30:
        correctness = 0
    elif "资料不足以确定" in answer:
        correctness = 0
        notes.append("非拒答题但出现保守回答")
        if not target_hit:
            notes.append("目标文档未命中")
    else:
        # 基于答案结构和内容判断
        has_structure = bool(re.search(r'#{1,3}\s|^\d+[.)]\s|^\s*[-*]\s', answer, re.MULTILINE))
        has_rfc = has_rfc_reference(answer)
        answer_len = len(answer)

        if has_structure and answer_len > 200:
            correctness = 2
        elif answer_len > 80:
            correctness = 1
        else:
            correctness = 0

    # Completeness
    completeness = score_completeness_heuristic(answer)

    # Faithfulness
    faithfulness = score_faithfulness_heuristic(answer, contexts)

    # Retrieval relevance
    if target_hit and contexts_count >= 2:
        relevance = 2
    elif target_hit or contexts_count >= 2:
        relevance = 1
    else:
        relevance = 0
        notes.append("目标文档未命中")

    return {
        "correctness_score": correctness,
        "completeness_score": completeness,
        "faithfulness_score": faithfulness,
        "retrieval_relevance_score": relevance,
        "manual_notes": "，".join(notes),
    }


def score_completeness_heuristic(answer):
    if not answer or "资料不足以确定" in answer:
        return 0
    points = count_answer_points(answer)
    length = len(answer)
    if points >= 3 and length > 300:
        return 2
    elif length > 100:
        return 1
    else:
        return 0


def score_faithfulness_heuristic(answer, contexts):
    if not answer or "资料不足以确定" in answer:
        return 2  # 拒答是忠实的
    if not contexts:
        return 0

    # 用英文术语重叠度评估忠实度
    context_text = " ".join(contexts)
    ctx_terms = extract_english_terms(context_text)
    ans_terms = extract_english_terms(answer)

    if ctx_terms and ans_terms:
        overlap = len(ans_terms & ctx_terms) / len(ans_terms)
        if overlap >= 0.3:
            return 2
        elif overlap >= 0.1:
            return 1
        else:
            return 0
    return 1 if len(answer) > 50 else 0


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


def print_summary(run_dir, results_rows, scored_rows):
    n = len(scored_rows)
    # 排除拒答题后计算质量分
    non_refuse = [(r, s) for r, s in zip(results_rows, scored_rows)
                  if r.get("refused", "").strip() != "True"]
    nr_n = len(non_refuse)

    avg_c = sum(s["correctness_score"] for _, s in non_refuse) / nr_n if nr_n else 0
    avg_cm = sum(s["completeness_score"] for _, s in non_refuse) / nr_n if nr_n else 0
    avg_f = sum(s["faithfulness_score"] for _, s in non_refuse) / nr_n if nr_n else 0
    avg_r = sum(s["retrieval_relevance_score"] for _, s in non_refuse) / nr_n if nr_n else 0

    # 全量平均
    avg_c_all = sum(s["correctness_score"] for s in scored_rows) / n
    avg_cm_all = sum(s["completeness_score"] for s in scored_rows) / n
    avg_f_all = sum(s["faithfulness_score"] for s in scored_rows) / n
    avg_r_all = sum(s["retrieval_relevance_score"] for s in scored_rows) / n

    print(f"\n=== {run_dir} ===")
    print(f"  全量平均: 正确性={avg_c_all:.2f} 完整性={avg_cm_all:.2f} 忠实度={avg_f_all:.2f} 相关性={avg_r_all:.2f}")
    print(f"  排除拒答: 正确性={avg_c:.2f} 完整性={avg_cm:.2f} 忠实度={avg_f:.2f} 相关性={avg_r:.2f}")

    # 拒答统计
    refused = [r for r in results_rows if r.get("refused", "").strip() == "True"]
    should_refuse = [r for r in results_rows if r.get("should_refuse", "").strip() == "True"]
    tp = sum(1 for r in should_refuse if r.get("refused", "").strip() == "True")
    fn = len(should_refuse) - tp
    fp = len(refused) - tp
    print(f"  拒答: TP={tp} FP={fp} FN={fn} 成功率={tp}/{len(should_refuse)}={tp/len(should_refuse)*100:.0f}%")

    review = [s for s in scored_rows if s["manual_notes"]]
    if review:
        print(f"  需复核: {len(review)} 题")
        for s in review:
            idx = scored_rows.index(s)
            qid = results_rows[idx]["id"]
            print(f"    ID={qid}: {results_rows[idx]['question'][:45]} | {s['manual_notes']}")


if __name__ == "__main__":
    runs = sys.argv[1:] if len(sys.argv) > 1 else [
        "20260507_094531_prompt_v1",
        "20260430_230707_with_rewrite",
    ]

    for run_dir in runs:
        results = load_results(run_dir)
        scored = [score_single(r) for r in results]
        write_draft(run_dir, results, scored)
        print_summary(run_dir, results, scored)
