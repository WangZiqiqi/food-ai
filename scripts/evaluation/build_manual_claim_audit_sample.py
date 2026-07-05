#!/usr/bin/env python3
"""Build a reproducible manual claim/entity audit sample from the 850 graph."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_EXTRACTION = Path("data/processed/final_graph/food_ai_graph.json")
DEFAULT_JSON_OUTPUT = Path("data/evaluation/manual_claim_audit_sample_100.json")
DEFAULT_CSV_OUTPUT = Path("data/evaluation/manual_claim_audit_sample_100.csv")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sample_claims(claims: list[dict[str, Any]], sample_size: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    by_direction: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        direction = claim.get("direction") or "missing"
        by_direction[direction].append(claim)

    # Keep the audit useful for direction quality: include positive, neutral,
    # negative, and a small tail of altered/missing labels when available.
    targets = {
        "positive": round(sample_size * 0.45),
        "neutral": round(sample_size * 0.25),
        "negative": round(sample_size * 0.25),
    }
    tail_target = sample_size - sum(targets.values())
    selected = []
    selected_ids = set()

    for direction, target in targets.items():
        pool = by_direction.get(direction, [])
        picked = rng.sample(pool, min(target, len(pool)))
        selected.extend(picked)
        selected_ids.update(claim["claim_id"] for claim in picked)

    tail_pool = [
        claim
        for direction, group in by_direction.items()
        if direction not in targets
        for claim in group
        if claim["claim_id"] not in selected_ids
    ]
    if tail_pool and tail_target > 0:
        picked = rng.sample(tail_pool, min(tail_target, len(tail_pool)))
        selected.extend(picked)
        selected_ids.update(claim["claim_id"] for claim in picked)

    if len(selected) < sample_size:
        remaining = [claim for claim in claims if claim["claim_id"] not in selected_ids]
        selected.extend(rng.sample(remaining, sample_size - len(selected)))

    rng.shuffle(selected)
    return selected[:sample_size]


def audit_record(claim: dict[str, Any], index: int) -> dict[str, Any]:
    evidence = claim.get("evidence_list", [])
    first = evidence[0] if evidence else {}
    return {
        "audit_id": f"audit_{index:03d}",
        "claim_id": claim.get("claim_id"),
        "claim_text": claim.get("claim_text"),
        "subject_name": claim.get("subject_name"),
        "subject_type": claim.get("subject_type"),
        "object_name": claim.get("object_name"),
        "object_type": claim.get("object_type"),
        "direction": claim.get("direction"),
        "effect_direction": claim.get("effect_direction", ""),
        "health_interpretation": claim.get("health_interpretation", ""),
        "evidence_count": claim.get("evidence_count", len(evidence)),
        "confidence_score": claim.get("confidence_score"),
        "primary_pmid": str(first.get("pmid", "")),
        "primary_study_type": first.get("study_type"),
        "primary_evidence_snippet": first.get("evidence_snippet"),
        "all_pmids": sorted({str(ev.get("pmid")) for ev in evidence if ev.get("pmid")}),
        "audit_subject_correct": "",
        "audit_outcome_correct": "",
        "audit_direction_correct": "",
        "audit_snippet_supports_claim": "",
        "audit_pmid_traceable": "",
        "audit_notes": "",
    }


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "audit_id",
        "claim_id",
        "claim_text",
        "subject_name",
        "subject_type",
        "object_name",
        "object_type",
        "direction",
        "effect_direction",
        "health_interpretation",
        "evidence_count",
        "confidence_score",
        "primary_pmid",
        "primary_study_type",
        "primary_evidence_snippet",
        "all_pmids",
        "audit_subject_correct",
        "audit_outcome_correct",
        "audit_direction_correct",
        "audit_snippet_supports_claim",
        "audit_pmid_traceable",
        "audit_notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["all_pmids"] = ";".join(row["all_pmids"])
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction", type=Path, default=DEFAULT_EXTRACTION)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV_OUTPUT)
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260506)
    args = parser.parse_args()

    extraction = load_json(args.extraction)
    records = [
        audit_record(claim, index)
        for index, claim in enumerate(
            sample_claims(extraction["merged_claims"], args.sample_size, args.seed),
            start=1,
        )
    ]

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(
            {
                "source": str(args.extraction),
                "sample_size": args.sample_size,
                "seed": args.seed,
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_csv(args.csv_output, records)
    print(f"Wrote {len(records)} audit records to {args.json_output} and {args.csv_output}")


if __name__ == "__main__":
    main()
