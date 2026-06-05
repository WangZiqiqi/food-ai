"""
Batch quality checks for extraction outputs.

This module is intentionally deterministic and cheap so it can run at the end
of every extraction batch before any agentic review/refine stage.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


SUSPICIOUS_FOOD_PATTERNS = [
    r"^male(?:_| )",
    r"^female(?:_| )",
    r"^placebo$",
    r"^control(?:_| )",
    r"^comparison$",
    r"^intervention$",
    r"^conditioning_",
]


def _is_suspicious_food(name: str) -> bool:
    normalized = (name or "").strip().lower()
    return any(re.search(pattern, normalized) for pattern in SUSPICIOUS_FOOD_PATTERNS)


def _is_over_specific_food(name: str) -> bool:
    normalized = (name or "").strip().lower()
    return normalized.count("_") >= 4 or any(char.isdigit() for char in normalized)


def summarize_extraction_quality(payload: dict[str, Any]) -> dict[str, Any]:
    results = payload.get("results", [])
    merged_claims = payload.get("merged_claims", [])

    suspicious_foods = sorted(
        {
            claim.get("subject_name", "")
            for claim in merged_claims
            if claim.get("subject_type") == "food" and _is_suspicious_food(claim.get("subject_name", ""))
        }
    )

    over_specific_foods = sorted(
        {
            claim.get("subject_name", "")
            for claim in merged_claims
            if claim.get("subject_type") == "food" and _is_over_specific_food(claim.get("subject_name", ""))
        }
    )

    warnings_by_pmid = {
        item.get("pmid", ""): item.get("warnings", [])
        for item in results
        if item.get("warnings")
    }

    zero_claim_pmids = [item.get("pmid", "") for item in results if item.get("success") and not item.get("claims")]
    failed_pmids = [item.get("pmid", "") for item in results if not item.get("success")]
    top_foods = Counter(
        claim.get("subject_name", "")
        for claim in merged_claims
        if claim.get("subject_type") == "food" and claim.get("subject_name")
    ).most_common(10)

    return {
        "summary": {
            "articles_total": payload.get("total", len(results)),
            "articles_success": payload.get("success", 0),
            "articles_error": payload.get("error", 0),
            "merged_claims": payload.get("merged_claims_count", len(merged_claims)),
            "zero_claim_articles": len(zero_claim_pmids),
            "articles_with_warnings": len(warnings_by_pmid),
            "suspicious_food_entities": len(suspicious_foods),
            "over_specific_food_entities": len(over_specific_foods),
        },
        "zero_claim_pmids": zero_claim_pmids,
        "failed_pmids": failed_pmids,
        "warnings_by_pmid": warnings_by_pmid,
        "suspicious_foods": suspicious_foods,
        "over_specific_foods": over_specific_foods,
        "top_foods": top_foods,
        "review_recommendation": _build_recommendation(
            suspicious_foods=suspicious_foods,
            over_specific_foods=over_specific_foods,
            zero_claim_pmids=zero_claim_pmids,
            warnings_by_pmid=warnings_by_pmid,
        ),
    }


def _build_recommendation(
    *,
    suspicious_foods: list[str],
    over_specific_foods: list[str],
    zero_claim_pmids: list[str],
    warnings_by_pmid: dict[str, list[str]],
) -> dict[str, Any]:
    should_review = bool(suspicious_foods or over_specific_foods or warnings_by_pmid)
    reasons = []
    if suspicious_foods:
        reasons.append("suspicious_food_entities_detected")
    if over_specific_foods:
        reasons.append("over_specific_food_entities_detected")
    if warnings_by_pmid:
        reasons.append("build_time_validation_warnings_present")
    if len(zero_claim_pmids) >= 5:
        reasons.append("high_zero_claim_tail")

    return {
        "should_run_batch_review": should_review,
        "reasons": reasons or ["batch_looks_clean"],
    }


def load_and_summarize_extraction_quality(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    report = summarize_extraction_quality(payload)
    report["input_path"] = str(path)
    return report
