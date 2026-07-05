"""
Incremental batch review utilities.

These helpers compare a fresh extraction output against a baseline extraction
artifact so review can focus on deltas instead of the whole graph every time.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .build_quality import summarize_extraction_quality
except ImportError:
    from build_quality import summarize_extraction_quality


def _entity_names_by_type(payload: dict[str, Any], entity_type: str) -> set[str]:
    names: set[str] = set()
    for claim in payload.get("merged_claims", []):
        if claim.get("subject_type") == entity_type and claim.get("subject_name"):
            names.add(claim["subject_name"])
        if claim.get("object_type") == entity_type and claim.get("object_name"):
            names.add(claim["object_name"])
    return names


def compare_extraction_batches(
    current_payload: dict[str, Any],
    baseline_payload: dict[str, Any],
) -> dict[str, Any]:
    current_quality = summarize_extraction_quality(current_payload)
    baseline_quality = summarize_extraction_quality(baseline_payload)

    current_claim_ids = {claim.get("claim_id") for claim in current_payload.get("merged_claims", []) if claim.get("claim_id")}
    baseline_claim_ids = {claim.get("claim_id") for claim in baseline_payload.get("merged_claims", []) if claim.get("claim_id")}

    current_foods = _entity_names_by_type(current_payload, "food")
    baseline_foods = _entity_names_by_type(baseline_payload, "food")
    current_outcomes = _entity_names_by_type(current_payload, "outcome")
    baseline_outcomes = _entity_names_by_type(baseline_payload, "outcome")

    new_claim_ids = sorted(current_claim_ids - baseline_claim_ids)
    removed_claim_ids = sorted(baseline_claim_ids - current_claim_ids)
    new_foods = sorted(current_foods - baseline_foods)
    removed_foods = sorted(baseline_foods - current_foods)
    new_outcomes = sorted(current_outcomes - baseline_outcomes)

    current_zero_claims = set(current_quality.get("zero_claim_pmids", []))
    baseline_zero_claims = set(baseline_quality.get("zero_claim_pmids", []))

    newly_suspicious_foods = sorted(
        set(current_quality.get("suspicious_foods", [])) - set(baseline_quality.get("suspicious_foods", []))
    )
    newly_over_specific_foods = sorted(
        set(current_quality.get("over_specific_foods", [])) - set(baseline_quality.get("over_specific_foods", []))
    )

    recommendation_reasons = []
    if newly_suspicious_foods:
        recommendation_reasons.append("new_suspicious_food_entities")
    if newly_over_specific_foods:
        recommendation_reasons.append("new_over_specific_food_entities")
    if len(new_foods) >= 10:
        recommendation_reasons.append("large_new_food_delta")
    if len(current_zero_claims) > len(baseline_zero_claims):
        recommendation_reasons.append("zero_claim_tail_worsened")

    return {
        "current_summary": current_quality["summary"],
        "baseline_summary": baseline_quality["summary"],
        "delta_summary": {
            "new_claims": len(new_claim_ids),
            "removed_claims": len(removed_claim_ids),
            "new_foods": len(new_foods),
            "removed_foods": len(removed_foods),
            "new_outcomes": len(new_outcomes),
            "zero_claim_articles_delta": len(current_zero_claims) - len(baseline_zero_claims),
            "newly_suspicious_foods": len(newly_suspicious_foods),
            "newly_over_specific_foods": len(newly_over_specific_foods),
        },
        "new_claim_ids": new_claim_ids[:100],
        "removed_claim_ids": removed_claim_ids[:100],
        "new_foods": new_foods[:100],
        "removed_foods": removed_foods[:100],
        "new_outcomes": new_outcomes[:100],
        "newly_suspicious_foods": newly_suspicious_foods,
        "newly_over_specific_foods": newly_over_specific_foods,
        "zero_claim_delta": {
            "current_only": sorted(current_zero_claims - baseline_zero_claims),
            "resolved_since_baseline": sorted(baseline_zero_claims - current_zero_claims),
        },
        "review_recommendation": {
            "should_run_batch_review": bool(recommendation_reasons),
            "reasons": recommendation_reasons or ["delta_looks_clean"],
        },
    }


def load_and_compare_extraction_batches(current_path: str | Path, baseline_path: str | Path) -> dict[str, Any]:
    current_payload = json.loads(Path(current_path).read_text(encoding="utf-8"))
    baseline_payload = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    report = compare_extraction_batches(current_payload, baseline_payload)
    report["current_input_path"] = str(current_path)
    report["baseline_input_path"] = str(baseline_path)
    return report
