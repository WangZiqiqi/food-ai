#!/usr/bin/env python3
"""Convert the external food-science question template into agent benchmark JSON."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_INPUT = Path("data/evaluation/external_food_science_questions_template_40.csv")
DEFAULT_OUTPUT = Path("data/evaluation/external_food_science_questions_40_benchmark.json")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--benchmark-id", default="external_food_science_questions_40")
    args = parser.parse_args()

    items = []
    for row in read_csv(args.input):
        question_type = row.get("question_type") or "external"
        expected_answer_type = (
            "no_answer" if question_type == "no_answer_candidate" else "external_review"
        )
        items.append(
            {
                "id": row["question_id"],
                "question": row["question"],
                "question_type": question_type,
                "expected_answer_type": expected_answer_type,
                "gold_claim_ids": [],
                "gold_pmids": [
                    pmid.strip()
                    for pmid in (row.get("expected_pmids_optional") or "").replace(";", ",").split(",")
                    if pmid.strip()
                ],
                "external_review": {
                    "authored_by": row.get("authored_by", ""),
                    "author_role": row.get("author_role", ""),
                    "expected_answer_notes": row.get("expected_answer_notes", ""),
                    "theme": row.get("theme", ""),
                    "difficulty": row.get("difficulty", ""),
                    "a_priori_expectation": row.get("a_priori_expectation", ""),
                },
            }
        )

    payload = {
        "benchmark_id": args.benchmark_id,
        "description": (
            "External-style food science questions authored independently of graph-derived "
            "gold claims. Results require qualitative review rather than graph-gold recall."
        ),
        "items": items,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
