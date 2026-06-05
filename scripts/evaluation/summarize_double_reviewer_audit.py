#!/usr/bin/env python3
"""Summarize two-reviewer claim audit agreement and resolved labels."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("data/evaluation/manual_claim_audit_double_reviewer_completed_30.csv")
DEFAULT_JSON = Path("data/evaluation/manual_claim_audit_double_reviewer_summary_30.json")
DEFAULT_MD = Path("data/evaluation/manual_claim_audit_double_reviewer_summary_30.md")

FIELDS = [
    "subject_correct",
    "outcome_correct",
    "direction_correct",
    "snippet_supports_claim",
    "pmid_traceable",
]
LABELS = {"yes", "no", "unclear"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    if not pairs:
        return None
    observed = sum(1 for left, right in pairs if left == right) / len(pairs)
    left_counts = Counter(left for left, _ in pairs)
    right_counts = Counter(right for _, right in pairs)
    expected = sum(
        (left_counts[label] / len(pairs)) * (right_counts[label] / len(pairs))
        for label in LABELS
    )
    if expected == 1:
        return 1.0
    return round((observed - expected) / (1 - expected), 4)


def metric_counts(rows: list[dict[str, str]], prefix: str, field: str) -> dict[str, Any]:
    key = f"{prefix}_{field}"
    counts = Counter((row.get(key) or "").strip().lower() for row in rows)
    yes = counts.get("yes", 0)
    no = counts.get("no", 0)
    unclear = counts.get("unclear", 0)
    denom = yes + no
    return {
        "yes": yes,
        "no": no,
        "unclear": unclear,
        "precision_excluding_unclear": round(yes / denom, 4) if denom else None,
        "yes_rate_all": round(yes / len(rows), 4) if rows else None,
        "unclear_rate_all": round(unclear / len(rows), 4) if rows else None,
    }


def summarize(rows: list[dict[str, str]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"count": len(rows), "agreement": {}, "resolved_metrics": {}}
    for field in FIELDS:
        pairs = []
        for row in rows:
            left = (row.get(f"reviewer1_{field}") or "").strip().lower()
            right = (row.get(f"reviewer2_{field}") or "").strip().lower()
            if left in LABELS and right in LABELS:
                pairs.append((left, right))
        agreement = sum(1 for left, right in pairs if left == right)
        summary["agreement"][field] = {
            "count": len(pairs),
            "agreements": agreement,
            "percent_agreement": round(agreement / len(pairs), 4) if pairs else None,
            "cohen_kappa": cohen_kappa(pairs),
        }
        summary["resolved_metrics"][field] = metric_counts(rows, "resolved", field)
    return summary


def render(summary: dict[str, Any]) -> str:
    lines = [
        "# Double-Reviewer Claim Audit Summary",
        "",
        f"Count: `{summary['count']}`",
        "",
        "## Reviewer Agreement",
        "| Field | Count | Agreement | Percent agreement | Cohen's kappa |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for field, metric in summary["agreement"].items():
        lines.append(
            f"| {field} | {metric['count']} | {metric['agreements']} | "
            f"{metric['percent_agreement']} | {metric['cohen_kappa']} |"
        )
    lines.extend(
        [
            "",
            "## Resolved Metrics",
            "| Field | Yes | No | Unclear | Precision excl. unclear | Yes rate all | Unclear rate all |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for field, metric in summary["resolved_metrics"].items():
        lines.append(
            f"| {field} | {metric['yes']} | {metric['no']} | {metric['unclear']} | "
            f"{metric['precision_excluding_unclear']} | {metric['yes_rate_all']} | "
            f"{metric['unclear_rate_all']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    rows = read_csv(args.input)
    summary = summarize(rows)
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.summary_md.write_text(render(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
