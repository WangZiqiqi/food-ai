#!/usr/bin/env python3
"""Run a vector-only claim citation baseline on a Food-AI QA benchmark.

This baseline does not call an answer-generation LLM. It retrieves claims using
the existing claim embedding index and treats selected retrieved claims as the
answer citations. For no-answer items, it abstains when the best retrieved
similarity is below a configurable threshold.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any


DEFAULT_BENCHMARK = Path("data/evaluation/query_benchmark_850_clean_120_plus_no_answer_25.json")
DEFAULT_OUTPUT = Path("data/evaluation/query_benchmark_850_vector_only_baseline.json")
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


def is_no_answer_item(item: dict[str, Any]) -> bool:
    return (
        item.get("expected_answer_type") == "no_answer"
        or item.get("question_type") in {"no_answer", "out_of_graph"}
    )


def reciprocal_rank(retrieved: list[str], gold: set[str]) -> float:
    for idx, claim_id in enumerate(retrieved, start=1):
        if claim_id in gold:
            return 1.0 / idx
    return 0.0


def retrieve_claims(
    item: dict[str, Any],
    vector_search,
    top_k: int,
    mode: str,
    strategy: str,
) -> tuple[list[tuple[str, str, float]], str, list[dict[str, Any]]]:
    queries = [item["question"]]
    if strategy == "oracle_reformulated" and not is_no_answer_item(item):
        queries = item.get("retrieval_queries") or queries

    by_claim_id: dict[str, tuple[str, float]] = {}
    mode_used_values = []
    query_traces = []
    for query in queries:
        results, mode_used = vector_search.search_claims(query, top_k=top_k, mode=mode)
        mode_used_values.append(mode_used)
        query_traces.append(
            {
                "query": query,
                "top_3": [
                    {"claim_id": claim_id, "claim_text": text, "similarity": score}
                    for claim_id, text, score in results[:3]
                ],
            }
        )
        for claim_id, text, score in results:
            current = by_claim_id.get(claim_id)
            if current is None or score > current[1]:
                by_claim_id[claim_id] = (text, score)

    ranked = sorted(by_claim_id.items(), key=lambda item_: item_[1][1], reverse=True)
    retrieved = [(claim_id, text, score) for claim_id, (text, score) in ranked[:top_k]]
    return retrieved, "+".join(sorted(set(mode_used_values))), query_traces


def evaluate_item(
    item: dict[str, Any],
    vector_search,
    claims_by_id: dict[str, dict[str, Any]],
    top_k: int,
    cite_k: int,
    mode: str,
    strategy: str,
    abstain_threshold: float,
) -> dict[str, Any]:
    retrieved, search_mode, query_traces = retrieve_claims(item, vector_search, top_k, mode, strategy)
    max_similarity = retrieved[0][2] if retrieved else 0.0
    no_answer_expected = is_no_answer_item(item)
    abstained = max_similarity < abstain_threshold

    cited = [] if abstained else retrieved[:cite_k]
    predicted_claims = {claim_id for claim_id, _text, _score in cited}
    predicted_pmids = pmids_for_claims(list(predicted_claims), claims_by_id)

    gold_claims = set(item.get("gold_claim_ids", []))
    gold_pmids = set(str(pmid) for pmid in item.get("gold_pmids", []))
    claim_hits = predicted_claims & gold_claims
    pmid_hits = predicted_pmids & gold_pmids

    return {
        "id": item["id"],
        "question_type": item["question_type"],
        "question": item["question"],
        "expected_answer_type": item.get("expected_answer_type", "graph_positive"),
        "strategy": strategy,
        "search_mode": search_mode,
        "top_k": top_k,
        "cite_k": cite_k,
        "abstain_threshold": abstain_threshold,
        "max_similarity": max_similarity,
        "abstained": abstained,
        "gold_claim_ids": sorted(gold_claims),
        "gold_pmids": sorted(gold_pmids),
        "predicted_claim_ids": sorted(predicted_claims),
        "predicted_pmids": sorted(predicted_pmids),
        "claim_hit": None if no_answer_expected else (1.0 if claim_hits else 0.0),
        "claim_recall": None
        if no_answer_expected
        else (len(claim_hits) / len(gold_claims) if gold_claims else 0.0),
        "pmid_hit": None if no_answer_expected else (1.0 if pmid_hits else 0.0),
        "pmid_recall": None
        if no_answer_expected
        else (len(pmid_hits) / len(gold_pmids) if gold_pmids else 0.0),
        "mrr": None if no_answer_expected else reciprocal_rank([r[0] for r in retrieved], gold_claims),
        "no_answer_correct": abstained if no_answer_expected else None,
        "query_traces": query_traces,
        "retrieved": [
            {
                "rank": idx,
                "claim_id": claim_id,
                "claim_text": text,
                "similarity": score,
                "cited": claim_id in predicted_claims,
                "is_gold_claim": claim_id in gold_claims,
                "evidence_pmids": sorted(pmids_for_claims([claim_id], claims_by_id)),
            }
            for idx, (claim_id, text, score) in enumerate(retrieved, start=1)
        ],
    }


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {"count": 0}
    graph_positive = [
        item for item in items if item.get("expected_answer_type", "graph_positive") != "no_answer"
    ]
    no_answer = [item for item in items if item.get("expected_answer_type") == "no_answer"]
    summary = {
        "count": len(items),
        "avg_cited_claims": round(mean(len(item["predicted_claim_ids"]) for item in items), 2),
        "avg_max_similarity": round(mean(item["max_similarity"] for item in items), 4),
    }
    if graph_positive:
        summary.update(
            {
                "graph_positive_count": len(graph_positive),
                "claim_hit": round(mean(item["claim_hit"] for item in graph_positive), 4),
                "claim_recall": round(mean(item["claim_recall"] for item in graph_positive), 4),
                "pmid_hit": round(mean(item["pmid_hit"] for item in graph_positive), 4),
                "pmid_recall": round(mean(item["pmid_recall"] for item in graph_positive), 4),
                "mrr": round(mean(item["mrr"] for item in graph_positive), 4),
                "false_abstention_rate": round(
                    mean(1.0 if item["abstained"] else 0.0 for item in graph_positive),
                    4,
                ),
            }
        )
    if no_answer:
        summary.update(
            {
                "no_answer_count": len(no_answer),
                "no_answer_correct": round(
                    mean(1.0 if item["no_answer_correct"] else 0.0 for item in no_answer),
                    4,
                ),
                "abstention_rate": round(
                    mean(1.0 if item["abstained"] else 0.0 for item in no_answer),
                    4,
                ),
            }
        )

    by_type = {}
    for qtype in sorted({item["question_type"] for item in items}):
        group = [item for item in items if item["question_type"] == qtype]
        group_summary = {
            "count": len(group),
            "avg_cited_claims": round(mean(len(item["predicted_claim_ids"]) for item in group), 2),
            "avg_max_similarity": round(mean(item["max_similarity"] for item in group), 4),
        }
        if all(item.get("expected_answer_type", "graph_positive") == "no_answer" for item in group):
            group_summary["no_answer_correct"] = round(
                mean(1.0 if item["no_answer_correct"] else 0.0 for item in group),
                4,
            )
            group_summary["abstention_rate"] = round(
                mean(1.0 if item["abstained"] else 0.0 for item in group),
                4,
            )
        else:
            positive_group = [
                item for item in group if item.get("expected_answer_type", "graph_positive") != "no_answer"
            ]
            group_summary.update(
                {
                    "claim_hit": round(mean(item["claim_hit"] for item in positive_group), 4),
                    "claim_recall": round(mean(item["claim_recall"] for item in positive_group), 4),
                    "pmid_hit": round(mean(item["pmid_hit"] for item in positive_group), 4),
                    "pmid_recall": round(mean(item["pmid_recall"] for item in positive_group), 4),
                    "mrr": round(mean(item["mrr"] for item in positive_group), 4),
                    "false_abstention_rate": round(
                        mean(1.0 if item["abstained"] else 0.0 for item in positive_group),
                        4,
                    ),
                }
            )
        by_type[qtype] = group_summary
    summary["by_question_type"] = by_type
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--vector-search", type=Path, default=DEFAULT_VECTOR_SEARCH)
    parser.add_argument("--extraction", type=Path, default=DEFAULT_EXTRACTION)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--cite-k", type=int, default=10)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--abstain-threshold", type=float, default=0.0)
    parser.add_argument(
        "--mode",
        choices=["auto", "embedding", "lexical"],
        default="auto",
        help="Search mode passed to vector_search.py.",
    )
    parser.add_argument(
        "--strategy",
        choices=["natural", "oracle_reformulated"],
        default="natural",
        help="Use only the natural question or gold-derived reformulated queries for graph-positive items.",
    )
    args = parser.parse_args()

    benchmark = load_json(args.benchmark)
    claims_by_id = claim_lookup(args.extraction)
    vector_search = load_vector_search(args.vector_search)

    benchmark_items = benchmark["items"][args.offset :]
    if args.limit:
        benchmark_items = benchmark_items[: args.limit]

    items = []
    for idx, item in enumerate(benchmark_items, start=1):
        print(f"[{idx}/{len(benchmark_items)}] {item['id']} {item['question_type']}", flush=True)
        items.append(
            evaluate_item(
                item,
                vector_search,
                claims_by_id,
                args.top_k,
                args.cite_k,
                args.mode,
                args.strategy,
                args.abstain_threshold,
            )
        )

    payload = {
        "benchmark_id": benchmark.get("benchmark_id"),
        "benchmark_path": str(args.benchmark),
        "baseline": "vector_only_claim_citation",
        "search_mode_requested": args.mode,
        "strategy": args.strategy,
        "top_k": args.top_k,
        "cite_k": args.cite_k,
        "limit": args.limit,
        "offset": args.offset,
        "abstain_threshold": args.abstain_threshold,
        "summary": summarize(items),
        "items": items,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote results to {args.output}")


if __name__ == "__main__":
    main()
