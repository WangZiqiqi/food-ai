#!/usr/bin/env python3
"""Audit compatibility between a benchmark built on one extraction and another graph.

The benchmark gold claim IDs are graph-version-specific. This script therefore
uses PMID, subject, and outcome anchors to explain whether degraded benchmark
scores come from evidence coverage loss, schema/name changes, or retrieval rank.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")


def token_set(text: str) -> set[str]:
    return {tok for tok in normalize(text).split("_") if tok}


def jaccard(a: str, b: str) -> float:
    ta = token_set(a)
    tb = token_set(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def claim_pmids(claim: dict[str, Any]) -> set[str]:
    return {
        str(ev.get("pmid", "")).strip()
        for ev in claim.get("evidence_list", []) or []
        if str(ev.get("pmid", "")).strip()
    }


def index_claims(extraction: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_id = {}
    by_pmid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in extraction.get("merged_claims", []) or []:
        claim_id = claim.get("claim_id")
        if claim_id:
            by_id[claim_id] = claim
        for pmid in claim_pmids(claim):
            by_pmid[pmid].append(claim)
    return by_id, by_pmid


def retrieved_pmids(item_result: dict[str, Any], k: int) -> set[str]:
    pmids = set()
    for row in item_result.get("retrieved", [])[:k]:
        pmids.update(str(pmid) for pmid in row.get("evidence_pmids", []) or [])
    return pmids


def best_anchor_match(
    claims: list[dict[str, Any]],
    gold_subjects: list[str],
    gold_outcomes: list[str],
) -> dict[str, Any]:
    best = {
        "score": 0.0,
        "subject_score": 0.0,
        "outcome_score": 0.0,
        "claim_id": None,
        "claim_text": None,
        "subject_name": None,
        "object_name": None,
    }
    for claim in claims:
        subject = claim.get("subject_name", "")
        outcome = claim.get("object_name", "")
        subject_score = max([jaccard(subject, gold) for gold in gold_subjects] or [0.0])
        outcome_score = max([jaccard(outcome, gold) for gold in gold_outcomes] or [0.0])
        score = (subject_score + outcome_score) / 2
        if score > best["score"]:
            best = {
                "score": round(score, 4),
                "subject_score": round(subject_score, 4),
                "outcome_score": round(outcome_score, 4),
                "claim_id": claim.get("claim_id"),
                "claim_text": claim.get("claim_text"),
                "subject_name": subject,
                "object_name": outcome,
            }
    return best


def classify_item(
    benchmark_item: dict[str, Any],
    result_item: dict[str, Any],
    by_pmid: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    gold_pmids = set(str(pmid) for pmid in benchmark_item.get("gold_pmids", []))
    gold_subjects = [normalize(x) for x in benchmark_item.get("gold_subjects", [])]
    gold_outcomes = [normalize(x) for x in benchmark_item.get("gold_outcomes", [])]

    graph_claims_for_gold_pmids = []
    graph_pmids_present = set()
    for pmid in gold_pmids:
        claims = by_pmid.get(pmid, [])
        if claims:
            graph_pmids_present.add(pmid)
            graph_claims_for_gold_pmids.extend(claims)

    top10_pmids = retrieved_pmids(result_item, 10)
    top20_pmids = retrieved_pmids(result_item, 20)
    top10_hit_pmids = gold_pmids & top10_pmids
    top20_hit_pmids = gold_pmids & top20_pmids

    best = best_anchor_match(graph_claims_for_gold_pmids, gold_subjects, gold_outcomes)
    exactish_anchor_present = best["subject_score"] >= 0.8 and best["outcome_score"] >= 0.8
    outcome_present = best["outcome_score"] >= 0.8
    subject_present = best["subject_score"] >= 0.8

    if not graph_pmids_present:
        category = "gold_pmids_absent_from_new_graph"
    elif len(top10_hit_pmids) == len(gold_pmids):
        category = "all_gold_pmids_retrieved_top10"
    elif top10_hit_pmids:
        category = "partial_gold_pmids_retrieved_top10"
    elif top20_hit_pmids:
        category = "gold_pmids_rank_11_20"
    elif exactish_anchor_present:
        category = "anchor_claim_present_but_not_retrieved_top20"
    elif subject_present or outcome_present:
        category = "gold_pmids_present_but_anchor_changed"
    else:
        category = "gold_pmids_present_but_no_close_anchor"

    return {
        "id": benchmark_item["id"],
        "question_type": benchmark_item.get("question_type"),
        "question": benchmark_item.get("question"),
        "gold_pmids_count": len(gold_pmids),
        "graph_gold_pmids_present": len(graph_pmids_present),
        "top10_gold_pmids": len(top10_hit_pmids),
        "top20_gold_pmids": len(top20_hit_pmids),
        "gold_pmid_coverage_in_graph": round(len(graph_pmids_present) / len(gold_pmids), 4) if gold_pmids else 0.0,
        "gold_pmid_recall_top10": round(len(top10_hit_pmids) / len(gold_pmids), 4) if gold_pmids else 0.0,
        "gold_pmid_recall_top20": round(len(top20_hit_pmids) / len(gold_pmids), 4) if gold_pmids else 0.0,
        "missing_from_graph_pmids": sorted(gold_pmids - graph_pmids_present),
        "missing_from_top10_pmids": sorted(gold_pmids - top10_hit_pmids),
        "category": category,
        "best_anchor_match": best,
        "top3": [
            {
                "rank": row.get("rank"),
                "claim_id": row.get("claim_id"),
                "claim_text": row.get("claim_text"),
                "similarity": round(row.get("similarity", 0.0), 4),
                "evidence_pmids": row.get("evidence_pmids", []),
            }
            for row in result_item.get("retrieved", [])[:3]
        ],
    }


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    category_counts = Counter(item["category"] for item in items)
    by_type: dict[str, Counter] = defaultdict(Counter)
    for item in items:
        by_type[item["question_type"]][item["category"]] += 1

    def avg(field: str) -> float:
        return round(sum(item[field] for item in items) / total, 4) if total else 0.0

    return {
        "count": total,
        "avg_gold_pmid_coverage_in_graph": avg("gold_pmid_coverage_in_graph"),
        "avg_gold_pmid_recall_top10": avg("gold_pmid_recall_top10"),
        "avg_gold_pmid_recall_top20": avg("gold_pmid_recall_top20"),
        "category_counts": dict(category_counts.most_common()),
        "by_question_type": {key: dict(counter.most_common()) for key, counter in sorted(by_type.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--extraction", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    benchmark = load_json(args.benchmark)
    extraction = load_json(args.extraction)
    results = load_json(args.results)
    _by_id, by_pmid = index_claims(extraction)
    results_by_id = {item["id"]: item for item in results.get("items", [])}

    audit_items = []
    for item in benchmark.get("items", []):
        if item["id"] not in results_by_id:
            continue
        audit_items.append(classify_item(item, results_by_id[item["id"]], by_pmid))

    payload = {
        "benchmark": str(args.benchmark),
        "extraction": str(args.extraction),
        "results": str(args.results),
        "summary": summarize(audit_items),
        "items": audit_items,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
