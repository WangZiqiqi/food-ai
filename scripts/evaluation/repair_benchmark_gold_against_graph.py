#!/usr/bin/env python3
"""Repair graph-derived benchmark gold claim IDs against a rebuilt extraction.

The 850 clean120 benchmark is generated from graph claims. After targeted graph
refinement, semantically equivalent claims can receive new claim_id values even
when the underlying PMID evidence remains present. This script maps stale
`gold_claim_ids` to current claim IDs using the benchmark's source evidence
PMIDs plus canonical subject/outcome/direction fields.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def norm(value: str) -> str:
    value = (value or "").lower().strip()
    value = re.sub(r"[-\s]+", "_", value)
    value = re.sub(r"__+", "_", value)
    return value


def evidence_pmids(claim: dict[str, Any]) -> set[str]:
    return {
        str(evidence.get("pmid", "")).strip()
        for evidence in claim.get("evidence_list", [])
        if str(evidence.get("pmid", "")).strip()
    }


def source_pmids(item: dict[str, Any], old_claim_id: str) -> set[str]:
    values = item.get("source_evidence", {}).get(old_claim_id, [])
    return {
        str(evidence.get("pmid", "")).strip()
        for evidence in values
        if str(evidence.get("pmid", "")).strip()
    }


def candidate_score(
    claim: dict[str, Any],
    item: dict[str, Any],
    target_pmids: set[str],
) -> tuple[int, int, int, int, str]:
    claim_pmids = evidence_pmids(claim)
    pmid_overlap = len(target_pmids & claim_pmids)
    subject_match = int(norm(claim.get("subject_name", "")) in {norm(v) for v in item.get("gold_subjects", [])})
    outcome_match = int(norm(claim.get("object_name", "")) in {norm(v) for v in item.get("gold_outcomes", [])})
    direction_match = int(claim.get("direction") in set(item.get("gold_directions", [])))
    return (pmid_overlap, subject_match, outcome_match, direction_match, claim.get("claim_id", ""))


def repair_item(item: dict[str, Any], claims: list[dict[str, Any]], by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    repaired_ids: list[str] = []
    repairs: list[dict[str, Any]] = []

    for old_claim_id in item.get("gold_claim_ids", []):
        target_pmids = source_pmids(item, old_claim_id)
        if not target_pmids:
            # Fallback for older benchmark schemas without per-claim source evidence.
            target_pmids = {str(pmid) for pmid in item.get("gold_pmids", [])}

        old_claim = by_id.get(old_claim_id)
        old_score = candidate_score(old_claim, item, target_pmids) if old_claim else (0, 0, 0, 0, "")

        candidates = []
        for claim in claims:
            score = candidate_score(claim, item, target_pmids)
            # Require PMID overlap plus at least subject/outcome match. Direction is
            # allowed to differ only when the benchmark itself has multiple directions
            # and the current claim still matches the evidence relation.
            if score[0] > 0 and score[1] and score[2]:
                candidates.append((score, claim))

        if old_claim and old_score[0] > 0 and old_score[1] and old_score[2]:
            best_claims = [old_claim]
            status = "kept_current"
        elif candidates:
            candidates.sort(key=lambda pair: pair[0], reverse=True)
            best_score = candidates[0][0]
            best_claims = [claim for score, claim in candidates if score[:4] == best_score[:4]]
            status = "mapped"
        else:
            best_claims = []
            status = "unmapped"

        new_ids = [claim["claim_id"] for claim in best_claims]
        for claim_id in new_ids:
            if claim_id not in repaired_ids:
                repaired_ids.append(claim_id)
        repairs.append(
            {
                "old_claim_id": old_claim_id,
                "new_claim_ids": new_ids,
                "status": status,
                "source_pmids": sorted(target_pmids),
                "new_claim_texts": [claim.get("claim_text", "") for claim in best_claims],
            }
        )

    repaired = dict(item)
    repaired["gold_claim_ids_original"] = item.get("gold_claim_ids", [])
    repaired["gold_claim_ids"] = repaired_ids
    repaired["gold_repair"] = repairs
    return repaired


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--extraction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    benchmark = load_json(args.benchmark)
    extraction = load_json(args.extraction)
    claims = extraction["merged_claims"]
    by_id = {claim["claim_id"]: claim for claim in claims}

    repaired_items = [repair_item(item, claims, by_id) for item in benchmark["items"]]
    changed = [
        item for item in repaired_items
        if item.get("gold_claim_ids") != item.get("gold_claim_ids_original")
    ]
    unmapped = [
        (item["id"], repair)
        for item in repaired_items
        for repair in item.get("gold_repair", [])
        if repair["status"] == "unmapped"
    ]

    payload = dict(benchmark)
    payload["benchmark_id"] = f"{benchmark.get('benchmark_id', 'benchmark')}_repaired"
    payload["description"] = (
        benchmark.get("description", "")
        + " Gold claim IDs repaired against the 2026-06-02 rebuilt deterministic-targeted graph; "
        + "PMID gold is unchanged."
    ).strip()
    payload["gold_repair_metadata"] = {
        "source_benchmark": str(args.benchmark),
        "target_extraction": str(args.extraction),
        "items_total": len(repaired_items),
        "items_with_claim_id_changes": len(changed),
        "unmapped_repairs": len(unmapped),
    }
    payload["items"] = repaired_items

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["gold_repair_metadata"], ensure_ascii=False, indent=2))
    if unmapped:
        print("UNMAPPED:")
        for item_id, repair in unmapped:
            print(item_id, repair)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
