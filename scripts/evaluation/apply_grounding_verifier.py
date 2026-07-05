#!/usr/bin/env python3
"""Attach sentence-grounding verifier labels to extracted graph claims."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_EXTRACTION = Path("data/processed/final_graph/food_ai_graph.json")
DEFAULT_VERIFIER = Path("data/evaluation/sentence_grounding_verifier_100.jsonl")
DEFAULT_OUTPUT = Path("data/processed/final_graph/food_ai_graph_grounding_annotated.json")
DEFAULT_SUMMARY = Path("data/evaluation/sentence_grounding_verifier_annotated_summary.md")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def high_confidence(row: dict[str, Any]) -> bool:
    return (
        row.get("support_label") == "supports"
        and row.get("direction_supported") == "yes"
        and float(row.get("confidence") or 0) >= 0.7
        and bool(row.get("best_sentence"))
    )


def verifier_annotation(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "support_label": row.get("support_label"),
        "direction_label": row.get("direction_label"),
        "effect_direction": row.get("effect_direction"),
        "health_interpretation": row.get("health_interpretation"),
        "direction_supported": row.get("direction_supported"),
        "best_sentence": row.get("best_sentence"),
        "best_sentence_id": row.get("best_sentence_id"),
        "best_sentence_source": row.get("best_sentence_source"),
        "confidence": row.get("confidence"),
        "reason": row.get("reason"),
        "model": row.get("model"),
        "verified_at": row.get("verified_at"),
        "high_confidence_grounded": high_confidence(row),
    }


def summarize(verifier_rows: list[dict[str, Any]], annotated_claims: int) -> str:
    support = Counter(row.get("support_label") for row in verifier_rows)
    direction_supported = Counter(row.get("direction_supported") for row in verifier_rows)
    effect = Counter(row.get("effect_direction") for row in verifier_rows)
    health = Counter(row.get("health_interpretation") for row in verifier_rows)
    high_conf = sum(1 for row in verifier_rows if high_confidence(row))

    lines = [
        "# Grounding-Annotated Graph Summary",
        "",
        f"Generated: `{datetime.now().isoformat(timespec='seconds')}`",
        f"Verifier rows: `{len(verifier_rows)}`",
        f"Annotated claims: `{annotated_claims}`",
        f"High-confidence grounded claims: `{high_conf}`",
        "",
        "## Support Labels",
        "| Label | Count |",
        "| --- | ---: |",
    ]
    for label in ("supports", "contradicts", "insufficient"):
        lines.append(f"| {label} | {support.get(label, 0)} |")

    lines.extend(["", "## Original Direction Supported", "| Label | Count |", "| --- | ---: |"])
    for label in ("yes", "no", "unclear"):
        lines.append(f"| {label} | {direction_supported.get(label, 0)} |")

    lines.extend(["", "## Measured Effect Directions", "| Label | Count |", "| --- | ---: |"])
    for label in ("increased", "decreased", "changed", "no_significant_effect", "associated", "mixed", "unclear"):
        lines.append(f"| {label} | {effect.get(label, 0)} |")

    lines.extend(["", "## Health Interpretations", "| Label | Count |", "| --- | ---: |"])
    for label in ("beneficial", "harmful", "neutral", "mixed", "unclear"):
        lines.append(f"| {label} | {health.get(label, 0)} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction", type=Path, default=DEFAULT_EXTRACTION)
    parser.add_argument("--verifier-jsonl", type=Path, default=DEFAULT_VERIFIER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    extraction = load_json(args.extraction)
    verifier_rows = load_jsonl(args.verifier_jsonl)
    by_claim = {
        str(row.get("claim_id")): verifier_annotation(row)
        for row in verifier_rows
        if row.get("claim_id")
    }

    annotated = 0
    for claim in extraction.get("merged_claims", []):
        annotation = by_claim.get(str(claim.get("claim_id")))
        if not annotation:
            continue
        claim["grounding_verifier"] = annotation
        claim["effect_direction_verified"] = annotation.get("effect_direction") or "unclear"
        claim["health_interpretation_verified"] = annotation.get("health_interpretation") or "unclear"
        claim["grounding_status"] = annotation.get("support_label") or "unverified"
        claim["direction_supported"] = annotation.get("direction_supported") or "unclear"
        claim["high_confidence_grounded"] = bool(annotation.get("high_confidence_grounded"))
        annotated += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(extraction, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.summary_md.write_text(summarize(verifier_rows, annotated), encoding="utf-8")
    print(f"annotated {annotated} claims")
    print(f"wrote {args.output}")
    print(f"wrote {args.summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
