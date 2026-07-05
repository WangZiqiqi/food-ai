#!/usr/bin/env python3
"""Merge manual claim audit annotations and summarize quality metrics."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_SAMPLE = Path("data/evaluation/manual_claim_audit_sample_100.csv")
DEFAULT_ANNOTATIONS = [
    Path("data/evaluation/manual_claim_audit_annotations_part1.csv"),
    Path("data/evaluation/manual_claim_audit_annotations_part2.csv"),
    Path("data/evaluation/manual_claim_audit_annotations_part3.csv"),
    Path("data/evaluation/manual_claim_audit_annotations_part4.csv"),
]
DEFAULT_MERGED = Path("data/evaluation/manual_claim_audit_100_completed.csv")
DEFAULT_SUMMARY_JSON = Path("data/evaluation/manual_claim_audit_100_summary.json")
DEFAULT_SUMMARY_MD = Path("data/evaluation/manual_claim_audit_100_summary.md")

AUDIT_FIELDS = [
    "audit_subject_correct",
    "audit_outcome_correct",
    "audit_direction_correct",
    "audit_snippet_supports_claim",
    "audit_pmid_traceable",
]
ALLOWED_LABELS = {"yes", "no", "unclear"}


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
            raise FileNotFoundError(f"missing annotation file: {path}")
        for row in read_csv(path):
            audit_id = row.get("audit_id", "").strip()
            if not audit_id:
                raise ValueError(f"annotation without audit_id in {path}")
            if audit_id in annotations:
                raise ValueError(f"duplicate annotation for {audit_id}")
            for field in AUDIT_FIELDS:
                value = row.get(field, "").strip().lower()
                if value not in ALLOWED_LABELS:
                    raise ValueError(f"{audit_id} has invalid {field}: {value!r}")
                row[field] = value
            annotations[audit_id] = row
    return annotations


def summarize(rows: list[dict[str, str]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "count": len(rows),
        "metrics": {},
        "direction_distribution": dict(Counter(row.get("direction") or "missing" for row in rows)),
    }
    for field in AUDIT_FIELDS:
        counts = Counter((row.get(field) or "").strip().lower() for row in rows)
        metric = {
            "yes": counts.get("yes", 0),
            "no": counts.get("no", 0),
            "unclear": counts.get("unclear", 0),
        }
        denom = metric["yes"] + metric["no"]
        metric["precision_excluding_unclear"] = round(metric["yes"] / denom, 4) if denom else None
        metric["yes_rate_all"] = round(metric["yes"] / len(rows), 4) if rows else None
        metric["unclear_rate_all"] = round(metric["unclear"] / len(rows), 4) if rows else None
        summary["metrics"][field] = metric
    return summary


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Manual Claim Audit Summary",
        "",
        f"Count: `{summary['count']}`",
        "",
        "## Metrics",
        "| Field | Yes | No | Unclear | Precision excl. unclear | Yes rate all | Unclear rate all |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for field, metric in summary["metrics"].items():
        lines.append(
            "| {field} | {yes} | {no} | {unclear} | {precision} | {yes_rate} | {unclear_rate} |".format(
                field=field,
                yes=metric["yes"],
                no=metric["no"],
                unclear=metric["unclear"],
                precision=metric["precision_excluding_unclear"],
                yes_rate=metric["yes_rate_all"],
                unclear_rate=metric["unclear_rate_all"],
            )
        )
    lines.extend(["", "## Direction Distribution", "| Direction | Count |", "| --- | ---: |"])
    for direction, count in sorted(summary["direction_distribution"].items()):
        lines.append(f"| {direction} | {count} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--annotation", type=Path, action="append", dest="annotations")
    parser.add_argument("--merged", type=Path, default=DEFAULT_MERGED)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_SUMMARY_MD)
    args = parser.parse_args()

    annotation_paths = args.annotations or DEFAULT_ANNOTATIONS
    sample_rows = read_csv(args.sample)
    annotations = load_annotations(annotation_paths)

    missing = [row["audit_id"] for row in sample_rows if row["audit_id"] not in annotations]
    if missing:
        raise ValueError(f"missing annotations for {len(missing)} rows: {missing[:10]}")

    merged_rows = []
    for row in sample_rows:
        annotation = annotations[row["audit_id"]]
        for field in AUDIT_FIELDS + ["audit_notes"]:
            row[field] = annotation.get(field, "")
        merged_rows.append(row)

    fields = list(sample_rows[0].keys()) if sample_rows else []
    write_csv(args.merged, merged_rows, fields)

    summary = summarize(merged_rows)
    args.summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    args.summary_md.write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
