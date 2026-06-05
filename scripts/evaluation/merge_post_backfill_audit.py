#!/usr/bin/env python3
"""Merge post-backfill targeted audit annotations into a full audit table."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_PRE_AUDIT = Path("data/evaluation/manual_claim_audit_100_completed.csv")
DEFAULT_TARGETS = Path("data/evaluation/manual_claim_audit_post_backfill_targets.csv")
DEFAULT_ANNOTATIONS = [
    Path("data/evaluation/manual_claim_audit_post_backfill_annotations_part1.csv"),
    Path("data/evaluation/manual_claim_audit_post_backfill_annotations_part2.csv"),
    Path("data/evaluation/manual_claim_audit_post_backfill_annotations_part3.csv"),
]
DEFAULT_OUTPUT = Path("data/evaluation/manual_claim_audit_100_post_backfill_completed.csv")
DEFAULT_SUMMARY_JSON = Path("data/evaluation/manual_claim_audit_100_post_backfill_summary.json")
DEFAULT_SUMMARY_MD = Path("data/evaluation/manual_claim_audit_100_post_backfill_summary.md")

LABELS = {"yes", "no", "unclear"}
POST_FIELDS = ["audit_direction_correct_post", "audit_snippet_supports_claim_post"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_annotations(paths: list[Path]) -> dict[str, dict[str, str]]:
    annotations: dict[str, dict[str, str]] = {}
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)
        for row in read_csv(path):
            audit_id = row.get("audit_id", "").strip()
            if not audit_id:
                raise ValueError(f"missing audit_id in {path}")
            if audit_id in annotations:
                raise ValueError(f"duplicate annotation for {audit_id}")
            for field in POST_FIELDS:
                value = row.get(field, "").strip().lower()
                if value not in LABELS:
                    raise ValueError(f"{audit_id} invalid {field}: {value!r}")
                row[field] = value
            annotations[audit_id] = row
    return annotations


def metric(rows: list[dict[str, str]], field: str) -> dict[str, Any]:
    counts = Counter((row.get(field) or "").strip().lower() for row in rows)
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


def summarize(rows: list[dict[str, str]], target_ids: set[str]) -> dict[str, Any]:
    target_rows = [row for row in rows if row["audit_id"] in target_ids]
    return {
        "count": len(rows),
        "targeted_reaudit_count": len(target_rows),
        "metrics_all_100": {
            "audit_subject_correct": metric(rows, "audit_subject_correct"),
            "audit_outcome_correct": metric(rows, "audit_outcome_correct"),
            "audit_direction_correct": metric(rows, "audit_direction_correct"),
            "audit_snippet_supports_claim": metric(rows, "audit_snippet_supports_claim"),
            "audit_pmid_traceable": metric(rows, "audit_pmid_traceable"),
        },
        "metrics_targeted": {
            "audit_direction_correct": metric(target_rows, "audit_direction_correct"),
            "audit_snippet_supports_claim": metric(target_rows, "audit_snippet_supports_claim"),
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Manual Claim Audit Post-Backfill Summary",
        "",
        f"Count: `{summary['count']}`",
        f"Targeted re-audit count: `{summary['targeted_reaudit_count']}`",
        "",
        "## Metrics All 100",
        "| Field | Yes | No | Unclear | Precision excl. unclear | Yes rate all | Unclear rate all |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for field, data in summary["metrics_all_100"].items():
        lines.append(
            f"| {field} | {data['yes']} | {data['no']} | {data['unclear']} | "
            f"{data['precision_excluding_unclear']} | {data['yes_rate_all']} | {data['unclear_rate_all']} |"
        )
    lines.extend(
        [
            "",
            "## Targeted Re-Audit Rows",
            "| Field | Yes | No | Unclear | Precision excl. unclear | Yes rate targeted | Unclear rate targeted |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for field, data in summary["metrics_targeted"].items():
        lines.append(
            f"| {field} | {data['yes']} | {data['no']} | {data['unclear']} | "
            f"{data['precision_excluding_unclear']} | {data['yes_rate_all']} | {data['unclear_rate_all']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-audit", type=Path, default=DEFAULT_PRE_AUDIT)
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--annotation", type=Path, action="append", dest="annotations")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_SUMMARY_MD)
    args = parser.parse_args()

    rows = read_csv(args.pre_audit)
    targets = read_csv(args.targets)
    target_ids = {row["audit_id"] for row in targets}
    annotations = load_annotations(args.annotations or DEFAULT_ANNOTATIONS)
    missing = sorted(target_ids - set(annotations))
    if missing:
        raise ValueError(f"missing post-backfill annotations: {missing[:10]}")

    merged = []
    for row in rows:
        row = dict(row)
        annotation = annotations.get(row["audit_id"])
        if annotation:
            row["audit_direction_correct"] = annotation["audit_direction_correct_post"]
            row["audit_snippet_supports_claim"] = annotation["audit_snippet_supports_claim_post"]
            row["audit_notes"] = annotation.get("audit_post_notes", "")
        merged.append(row)

    fields = list(rows[0].keys()) if rows else []
    write_csv(args.output, merged, fields)
    summary = summarize(merged, target_ids)
    args.summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    args.summary_md.write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
