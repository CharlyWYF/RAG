from __future__ import annotations

import argparse
from pathlib import Path

from run_eval import DEFAULT_OUTPUT_DIR, DEFAULT_QUESTION_SET, run_evaluation
from src.qa import PROMPT_TEMPLATE_V2


def main() -> None:
    parser = argparse.ArgumentParser(description="Run automated QA evaluation with the v2 prompt template")
    parser.add_argument("--question-set", type=Path, default=DEFAULT_QUESTION_SET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--disable-query-rewrite", action="store_true")
    args = parser.parse_args()

    run_evaluation(
        question_set_path=args.question_set,
        output_dir=args.output_dir,
        enable_query_rewrite=not args.disable_query_rewrite,
        prompt_template=PROMPT_TEMPLATE_V2,
        run_name_suffix="prompt_v2",
    )


if __name__ == "__main__":
    main()
