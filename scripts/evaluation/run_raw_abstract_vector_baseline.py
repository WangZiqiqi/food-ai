#!/usr/bin/env python3
"""Evaluate document-level raw abstract vector retrieval on Food-AI QA benchmarks."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("SILICONFLOW_API_KEY")
API_URL = os.getenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1/embeddings")
MODEL = os.getenv("SILICONFLOW_MODEL", "BAAI/bge-m3")

DEFAULT_BENCHMARK = Path("data/evaluation/query_benchmark_850_clean_120_plus_no_answer_25.json")
DEFAULT_ABSTRACT_EMBEDDINGS = Path("data/processed/final_graph/abstract_embeddings_bge_m3.json")
DEFAULT_OUTPUT = Path("data/evaluation/query_benchmark_850_raw_abstract_vector_baseline.json")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def embed_query(text: str, max_retries: int, timeout: int) -> list[float]:
    if not API_KEY:
        raise RuntimeError("SILICONFLOW_API_KEY not set")
    payload = {
        "model": MODEL,
        "input": [text],
        "encoding_format": "float",
    }
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= max_retries:
                raise
            time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"embedding request failed: {last_error}")


def cosine_scores(query_embedding: list[float], embeddings: list[list[float]]) -> np.ndarray:
    matrix = np.asarray(embeddings, dtype=np.float32)
    query = np.asarray(query_embedding, dtype=np.float32)
    matrix_norms = np.linalg.norm(matrix, axis=1)
    query_norm = np.linalg.norm(query)
    return (matrix @ query) / (matrix_norms * query_norm)


def is_no_answer_item(item: dict[str, Any]) -> bool:
    return (
        item.get("expected_answer_type") == "no_answer"
        or item.get("question_type") in {"no_answer", "out_of_graph"}
    )


def evaluate_item(
    item: dict[str, Any],
    abstract_index: dict[str, Any],
    top_k: int,
    strategy: str,
    abstain_threshold: float,
    max_retries: int,
    timeout: int,
) -> dict[str, Any]:
    queries = [item["question"]]
    if strategy == "oracle_reformulated" and not is_no_answer_item(item):
        queries = item.get("retrieval_queries") or queries

    pmids = [str(pmid) for pmid in abstract_index["pmids"]]
    titles = abstract_index.get("titles", [""] * len(pmids))
    embeddings = abstract_index["embeddings"]
    best_by_idx: dict[int, tuple[float, str]] = {}
    query_traces = []

    for query in queries:
        query_embedding = embed_query(query, max_retries=max_retries, timeout=timeout)
        scores = cosine_scores(query_embedding, embeddings)
        ranked_indices = np.argsort(scores)[::-1][:top_k]
        query_traces.append(
            {
                "query": query,
                "top_3": [
                    {
                        "pmid": pmids[int(idx)],
                        "title": titles[int(idx)],
                        "similarity": float(scores[int(idx)]),
                    }
                    for idx in ranked_indices[:3]
                ],
            }
        )
        for idx in ranked_indices:
            idx_int = int(idx)
            score = float(scores[idx_int])
            current = best_by_idx.get(idx_int)
            if current is None or score > current[0]:
                best_by_idx[idx_int] = (score, query)

    ranked = sorted(best_by_idx.items(), key=lambda row: row[1][0], reverse=True)[:top_k]
    retrieved_pmids = [pmids[idx] for idx, (_score, _query) in ranked]
    max_similarity = ranked[0][1][0] if ranked else 0.0
    abstained = max_similarity < abstain_threshold

    gold_pmids = set(str(pmid) for pmid in item.get("gold_pmids", []))
    no_answer_expected = is_no_answer_item(item)
    predicted_pmids = set() if abstained else set(retrieved_pmids)
    pmid_hits = predicted_pmids & gold_pmids

    metrics = {}
    for k in (1, 3, 5, 10, 20):
        if k > top_k:
            continue
        pmids_at_k = set() if abstained else set(retrieved_pmids[:k])
        hits_at_k = pmids_at_k & gold_pmids
        metrics[f"pmid_hit@{k}"] = None if no_answer_expected else (1.0 if hits_at_k else 0.0)
        metrics[f"pmid_recall@{k}"] = (
            None
            if no_answer_expected
            else (len(hits_at_k) / len(gold_pmids) if gold_pmids else 0.0)
        )

    return {
        "id": item["id"],
        "question_type": item["question_type"],
        "question": item["question"],
        "expected_answer_type": item.get("expected_answer_type", "graph_positive"),
        "strategy": strategy,
        "top_k": top_k,
        "abstain_threshold": abstain_threshold,
        "max_similarity": max_similarity,
        "abstained": abstained,
        "gold_pmids": sorted(gold_pmids),
        "predicted_pmids": sorted(predicted_pmids),
        "pmid_hit": None if no_answer_expected else (1.0 if pmid_hits else 0.0),
        "pmid_recall": None
        if no_answer_expected
        else (len(pmid_hits) / len(gold_pmids) if gold_pmids else 0.0),
        "no_answer_correct": abstained if no_answer_expected else None,
        "metrics": metrics,
        "query_traces": query_traces,
        "retrieved": [
            {
                "rank": rank,
                "pmid": pmids[idx],
                "title": titles[idx],
                "similarity": score,
                "matched_query": query,
                "is_gold_pmid": pmids[idx] in gold_pmids,
            }
            for rank, (idx, (score, query)) in enumerate(ranked, start=1)
        ],
    }


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    graph_positive = [
        item for item in items if item.get("expected_answer_type", "graph_positive") != "no_answer"
    ]
    no_answer = [item for item in items if item.get("expected_answer_type") == "no_answer"]

    metric_names = sorted(
        {
            name
            for item in graph_positive
            for name, value in item.get("metrics", {}).items()
            if value is not None
        }
    )
    summary: dict[str, Any] = {
        "count": len(items),
        "avg_max_similarity": round(mean(item["max_similarity"] for item in items), 4),
    }
    if graph_positive:
        summary["graph_positive_count"] = len(graph_positive)
        for name in metric_names:
            summary[name] = round(mean(item["metrics"][name] for item in graph_positive), 4)
        summary["pmid_hit"] = round(mean(item["pmid_hit"] for item in graph_positive), 4)
        summary["pmid_recall"] = round(mean(item["pmid_recall"] for item in graph_positive), 4)
        summary["false_abstention_rate"] = round(
            mean(1.0 if item["abstained"] else 0.0 for item in graph_positive),
            4,
        )
    if no_answer:
        summary["no_answer_count"] = len(no_answer)
        summary["no_answer_correct"] = round(
            mean(1.0 if item["no_answer_correct"] else 0.0 for item in no_answer),
            4,
        )
        summary["abstention_rate"] = round(
            mean(1.0 if item["abstained"] else 0.0 for item in no_answer),
            4,
        )

    by_type = {}
    for qtype in sorted({item["question_type"] for item in items}):
        group = [item for item in items if item["question_type"] == qtype]
        group_summary: dict[str, Any] = {
            "count": len(group),
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
            positives = [
                item for item in group if item.get("expected_answer_type", "graph_positive") != "no_answer"
            ]
            for name in metric_names:
                group_summary[name] = round(mean(item["metrics"][name] for item in positives), 4)
            group_summary["pmid_hit"] = round(mean(item["pmid_hit"] for item in positives), 4)
            group_summary["pmid_recall"] = round(mean(item["pmid_recall"] for item in positives), 4)
            group_summary["false_abstention_rate"] = round(
                mean(1.0 if item["abstained"] else 0.0 for item in positives),
                4,
            )
        by_type[qtype] = group_summary
    summary["by_question_type"] = by_type
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--abstract-embeddings", type=Path, default=DEFAULT_ABSTRACT_EMBEDDINGS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--abstain-threshold", type=float, default=0.0)
    parser.add_argument("--strategy", choices=["natural", "oracle_reformulated"], default="natural")
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()

    benchmark = load_json(args.benchmark)
    abstract_index = load_json(args.abstract_embeddings)

    items = []
    for idx, item in enumerate(benchmark["items"], start=1):
        print(f"[{idx}/{len(benchmark['items'])}] {item['id']} {item['question_type']}", flush=True)
        items.append(
            evaluate_item(
                item,
                abstract_index,
                args.top_k,
                args.strategy,
                args.abstain_threshold,
                args.max_retries,
                args.timeout,
            )
        )

    payload = {
        "benchmark_id": benchmark.get("benchmark_id"),
        "benchmark_path": str(args.benchmark),
        "baseline": "raw_abstract_document_vector",
        "abstract_embeddings": str(args.abstract_embeddings),
        "strategy": args.strategy,
        "top_k": args.top_k,
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
