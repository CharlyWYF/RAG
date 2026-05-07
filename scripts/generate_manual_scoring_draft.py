from __future__ import annotations

import argparse
import csv
from pathlib import Path


FIELDNAMES = [
    "id",
    "question",
    "protocol_group",
    "question_type",
    "target_document",
    "difficulty",
    "should_refuse",
    "section",
    "correctness_score",
    "completeness_score",
    "faithfulness_score",
    "retrieval_relevance_score",
    "manual_notes",
]


def load_results(results_path: Path) -> list[dict[str, str]]:
    with results_path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_scoring_rows(results_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    scoring_rows: list[dict[str, str]] = []
    for row in results_rows:
        scoring_rows.append({
            "id": row.get("id", ""),
            "question": row.get("question", ""),
            "protocol_group": row.get("protocol_group", ""),
            "question_type": row.get("question_type", ""),
            "target_document": row.get("target_document", ""),
            "difficulty": row.get("difficulty", ""),
            "should_refuse": row.get("should_refuse", ""),
            "section": row.get("section", ""),
            "correctness_score": "",
            "completeness_score": "",
            "faithfulness_score": "",
            "retrieval_relevance_score": "",
            "manual_notes": "",
        })
    return scoring_rows


def write_scoring(path: Path, rows: list[dict[str, str]], force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists. Use --force to overwrite it.")

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def resolve_results_path(run_dir: Path) -> Path:
    results_path = run_dir / "results.csv"
    if not results_path.exists():
        raise FileNotFoundError(f"results.csv not found under {run_dir}")
    return results_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate manual scoring draft CSV from an evaluation run directory")
    parser.add_argument("run_dirs", nargs="+", type=Path, help="Evaluation run directories that contain results.csv")
    parser.add_argument("--force", action="store_true", help="Overwrite existing manual_scoring_draft.csv files")
    args = parser.parse_args()

    for run_dir in args.run_dirs:
        results_path = resolve_results_path(run_dir)
        out_path = run_dir / "manual_scoring_draft.csv"
        rows = build_scoring_rows(load_results(results_path))
        write_scoring(out_path, rows, force=args.force)
        print(f"[OK] 已生成: {out_path}")


if __name__ == "__main__":
    main()
