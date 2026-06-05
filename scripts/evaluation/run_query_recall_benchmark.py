#!/usr/bin/env python3
"""
Evaluate Query Agent retrieval recall on a fixed Food-AI QA benchmark.

This measures the recall of the graph-retrieval tool layer used by the
read-only Query Agent. It does not grade final natural-language answers.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any


DEFAULT_BENCHMARK = Path("data/evaluation/query_benchmark_850_seed.json")
DEFAULT_OUTPUT = Path("data/evaluation/query_benchmark_850_recall_results.json")
DEFAULT_VECTOR_SEARCH = Path(
    ".agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/vector_search.py"
)
DEFAULT_EXTRACTION = Path("data/processed/final_graph/food_ai_graph.json")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_vector_search(path: Path):
    sys.path.insert(0, str(path.parent.resolve()))
    spec = importlib.util.spec_from_file_location("food_ai_vector_search", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load vector_search module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def claim_lookup(extraction_path: Path) -> dict[str, dict[str, Any]]:
    extraction = load_json(extraction_path)
    return {claim["claim_id"]: claim for claim in extraction["merged_claims"]}


def pmids_for_claims(claim_ids: list[str], claims_by_id: dict[str, dict[str, Any]]) -> set[str]:
    pmids = set()
    for claim_id in claim_ids:
        claim = claims_by_id.get(claim_id)
        if not claim:
            continue
        for evidence in claim.get("evidence_list", []):
            pmid = str(evidence.get("pmid", "")).strip()
            if pmid:
                pmids.add(pmid)
    return pmids


def reciprocal_rank(retrieved: list[str], gold: set[str]) -> float:
    for idx, claim_id in enumerate(retrieved, start=1):
        if claim_id in gold:
            return 1.0 / idx
    return 0.0


def evaluate_item(
    item: dict[str, Any],
    vector_search,
    claims_by_id: dict[str, dict[str, Any]],
    max_k: int,
    mode: str,
    strategy: str,
) -> dict[str, Any]:
    queries = [item["question"]]
    if strategy == "oracle_reformulated":
        queries = item.get("retrieval_queries") or queries

    mode_used_values = []
    by_claim_id: dict[str, tuple[str, float]] = {}
    query_traces = []
    for query in queries:
        query_results, mode_used = vector_search.search_claims(query, top_k=max_k, mode=mode)
        mode_used_values.append(mode_used)
        query_traces.append(
            {
                "query": query,
                "top_3": [
                    {"claim_id": claim_id, "claim_text": text, "similarity": score}
                    for claim_id, text, score in query_results[:3]
                ],
            }
        )
        for claim_id, text, score in query_results:
            current = by_claim_id.get(claim_id)
            if current is None or score > current[1]:
                by_claim_id[claim_id] = (text, score)

    results = sorted(by_claim_id.items(), key=lambda item_: item_[1][1], reverse=True)[:max_k]
    retrieved_claim_ids = [claim_id for claim_id, (_text, _score) in results]
    retrieved_pmids_by_k = {}
    for k in (1, 3, 5, 10, 20):
        if k <= max_k:
            retrieved_pmids_by_k[k] = pmids_for_claims(retrieved_claim_ids[:k], claims_by_id)

    gold_claims = set(item["gold_claim_ids"])
    gold_pmids = set(str(pmid) for pmid in item["gold_pmids"])

    metrics = {}
    for k in (1, 3, 5, 10, 20):
        if k > max_k:
            continue
        retrieved_at_k = set(retrieved_claim_ids[:k])
        claim_hits = retrieved_at_k & gold_claims
        pmid_hits = retrieved_pmids_by_k[k] & gold_pmids
        metrics[f"claim_hit@{k}"] = 1.0 if claim_hits else 0.0
        metrics[f"claim_recall@{k}"] = len(claim_hits) / len(gold_claims) if gold_claims else 0.0
        metrics[f"pmid_hit@{k}"] = 1.0 if pmid_hits else 0.0
        metrics[f"pmid_recall@{k}"] = len(pmid_hits) / len(gold_pmids) if gold_pmids else 0.0

    return {
        "id": item["id"],
        "question_type": item["question_type"],
        "question": item["question"],
        "gold_claim_ids": item["gold_claim_ids"],
        "gold_pmids": item["gold_pmids"],
        "search_mode": "+".join(sorted(set(mode_used_values))),
        "strategy": strategy,
        "query_traces": query_traces,
        "mrr": reciprocal_rank(retrieved_claim_ids, gold_claims),
        "metrics": metrics,
        "retrieved": [
            {
                "rank": idx,
                "claim_id": claim_id,
                "claim_text": text,
                "similarity": score,
                "is_gold_claim": claim_id in gold_claims,
                "evidence_pmids": sorted(pmids_for_claims([claim_id], claims_by_id)),
            }
            for idx, (claim_id, (text, score)) in enumerate(results, start=1)
        ],
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    metric_names = sorted({name for item in results for name in item["metrics"]})

    def avg(name: str) -> float:
        return round(mean(item["metrics"][name] for item in results), 4)

    pmid_names = [name for name in metric_names if name.startswith("pmid_")]
    claim_names = [name for name in metric_names if name.startswith("claim_")]

    primary = {name: avg(name) for name in pmid_names}
    self_consistency = {name: avg(name) for name in claim_names}
    self_consistency["mrr"] = round(mean(item["mrr"] for item in results), 4)
    self_consistency["_note"] = (
        "Claim-level recall measures index self-consistency: gold_claim_id IS the seed "
        "claim the question was generated from, so high recall is structural and does NOT "
        "indicate retrieval generalization. Use pmid_recall@k as the primary metric."
    )

    headline = {
        "primary_metric": "pmid_recall@10",
        "pmid_recall@10": primary.get("pmid_recall@10"),
        "pmid_hit@10": primary.get("pmid_hit@10"),
    }

    by_type = {}
    for qtype in sorted({item["question_type"] for item in results}):
        group = [item for item in results if item["question_type"] == qtype]
        entry = {
            "count": len(group),
            "mrr": round(mean(item["mrr"] for item in group), 4),
        }
        for name in metric_names:
            entry[name] = round(mean(item["metrics"][name] for item in group), 4)
        by_type[qtype] = entry

    pmid_misses = []
    for item in results:
        if item["metrics"].get("pmid_hit@10", 0.0) == 0.0:
            pmid_misses.append(
                {
                    "id": item["id"],
                    "question_type": item["question_type"],
                    "question": item["question"],
                    "gold_pmids": item["gold_pmids"],
                    "top_3": [
                        {
                            "claim_id": r["claim_id"],
                            "claim_text": r["claim_text"],
                            "evidence_pmids": r["evidence_pmids"],
                            "similarity": round(r["similarity"], 4),
                        }
                        for r in item["retrieved"][:3]
                    ],
                }
            )

    claim_misses = [
        {
            "id": item["id"],
            "question_type": item["question_type"],
            "question": item["question"],
            "gold_claim_ids": item["gold_claim_ids"],
        }
        for item in results
        if item["metrics"].get("claim_hit@10", 0.0) == 0.0
    ]

    return {
        "count": len(results),
        "headline": headline,
        "primary_pmid_metrics": primary,
        "index_self_consistency": self_consistency,
        "by_question_type": by_type,
        "pmid_misses_at_10": pmid_misses,
        "index_self_consistency_misses_at_10": claim_misses,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--vector-search", type=Path, default=DEFAULT_VECTOR_SEARCH)
    parser.add_argument("--extraction", type=Path, default=DEFAULT_EXTRACTION)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument(
        "--mode",
        choices=["auto", "embedding", "lexical"],
        default="auto",
        help="Search mode passed to vector_search.py",
    )
    parser.add_argument(
        "--strategy",
        choices=["natural", "oracle_reformulated"],
        default="natural",
        help=(
            "natural uses the benchmark question only; oracle_reformulated also uses "
            "gold subject/outcome canonical queries to estimate an agent-style anchor/query rewrite upper bound."
        ),
    )
    args = parser.parse_args()

    benchmark = load_json(args.benchmark)
    claims_by_id = claim_lookup(args.extraction)
    vector_search = load_vector_search(args.vector_search)

    results = []
    for idx, item in enumerate(benchmark["items"], start=1):
        print(f"[{idx}/{len(benchmark['items'])}] {item['id']} {item['question_type']}")
        results.append(evaluate_item(item, vector_search, claims_by_id, args.top_k, args.mode, args.strategy))

    payload = {
        "benchmark_id": benchmark.get("benchmark_id"),
        "benchmark_path": str(args.benchmark),
        "search_mode_requested": args.mode,
        "strategy": args.strategy,
        "top_k": args.top_k,
        "summary": summarize(results),
        "items": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hp = payload["summary"]["headline"]
    print(
        f"PRIMARY  pmid_recall@10 = {hp['pmid_recall@10']}  (pmid_hit@10 = {hp['pmid_hit@10']})"
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote results to {args.output}")


if __name__ == "__main__":
    main()
