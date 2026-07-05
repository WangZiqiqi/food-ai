#!/usr/bin/env python3
"""
Run the full Food-AI Query Agent on a QA benchmark and score returned evidence.

This evaluates the end-to-end SDK Agent path, not just vector retrieval.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import re
import sys
from pathlib import Path
from statistics import mean
from typing import Any


DEFAULT_BENCHMARK = Path("data/evaluation/query_benchmark_850_seed.json")
DEFAULT_OUTPUT = Path("data/evaluation/query_benchmark_850_agent_answer_results.json")
AGENT_PATH = Path("agents/kg_agent_query.py")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_agent_module(path: Path):
    sys.path.insert(0, str(path.parent.resolve()))
    spec = importlib.util.spec_from_file_location("food_ai_kg_agent_query", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Query Agent from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None

    fence = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    candidates = []
    if fence:
        candidates.append(fence.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def extract_pmids(answer_data: dict[str, Any] | None, raw_text: str) -> set[str]:
    pmids = set(re.findall(r"\bPMID[:\s]*(\d{6,9})\b", raw_text or "", re.IGNORECASE))
    if not answer_data:
        return pmids
    for entry in answer_data.get("evidence_summary", []) or []:
        if isinstance(entry, dict) and entry.get("pmid"):
            pmids.add(str(entry["pmid"]))
    return pmids


def extract_claims(answer_data: dict[str, Any] | None, raw_text: str) -> set[str]:
    claims = set(re.findall(r"\b[0-9a-f]{12}\b", raw_text or ""))
    if not answer_data:
        return claims
    for claim_id in answer_data.get("claims_referenced", []) or []:
        if isinstance(claim_id, str):
            claims.add(claim_id)
    return claims


def is_no_answer_item(item: dict[str, Any]) -> bool:
    return (
        item.get("expected_answer_type") == "no_answer"
        or item.get("question_type") in {"no_answer", "out_of_graph"}
    )


def detects_abstention(answer_data: dict[str, Any] | None, raw_text: str) -> bool:
    text = raw_text.lower() if raw_text else ""
    abstention_markers = (
        "no direct evidence",
        "no evidence",
        "not found",
        "could not find",
        "does not contain",
        "not contain",
        "insufficient evidence",
        "out of graph",
        "outside the graph",
        "no matching claim",
        "no relevant claim",
        "no direct claim",
        "no claim associating",
        "no direct graph",
        "no direct graph-backed",
        "no basis to recommend",
        "cannot cite any pmid",
        "cannot cite",
        "not supported",
        "does not support",
        "do not support",
    )
    if any(marker in text for marker in abstention_markers):
        return True
    if answer_data and str(answer_data.get("confidence", "")).lower() == "low":
        answer_text = str(answer_data.get("answer", "")).lower()
        return any(marker in answer_text for marker in abstention_markers)
    return False


def score_answer(item: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    raw = result.get("agent_response", "") or ""
    parsed = extract_json_object(raw)
    predicted_claims = extract_claims(parsed, raw)
    predicted_pmids = extract_pmids(parsed, raw)
    gold_claims = set(item.get("gold_claim_ids", []))
    gold_pmids = set(str(pmid) for pmid in item.get("gold_pmids", []))
    no_answer_expected = is_no_answer_item(item)

    claim_hits = predicted_claims & gold_claims
    pmid_hits = predicted_pmids & gold_pmids
    abstained = detects_abstention(parsed, raw)
    no_answer_correct = (
        abstained
        and not (predicted_claims & gold_claims)
        and not (predicted_pmids & gold_pmids)
        if no_answer_expected
        else None
    )
    return {
        "id": item["id"],
        "question_type": item["question_type"],
        "question": item["question"],
        "expected_answer_type": item.get("expected_answer_type", "graph_positive"),
        "success": bool(result.get("success")),
        "json_parse_success": parsed is not None,
        "tool_call_count": len(result.get("tool_calls", []) or []),
        "iterations": result.get("iterations"),
        "gold_claim_ids": sorted(gold_claims),
        "gold_pmids": sorted(gold_pmids),
        "predicted_claim_ids": sorted(predicted_claims),
        "predicted_pmids": sorted(predicted_pmids),
        "claim_hit": None if no_answer_expected or not gold_claims else (1.0 if claim_hits else 0.0),
        "claim_recall": None if no_answer_expected or not gold_claims else len(claim_hits) / len(gold_claims),
        "pmid_hit": None if no_answer_expected or not gold_pmids else (1.0 if pmid_hits else 0.0),
        "pmid_recall": None if no_answer_expected or not gold_pmids else len(pmid_hits) / len(gold_pmids),
        "abstained": abstained,
        "no_answer_correct": no_answer_correct,
        "answer_data": parsed,
        "raw_agent_response": raw,
        "tool_calls": result.get("tool_calls", []),
        "error": result.get("error"),
    }


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {"count": 0}

    graph_positive = [item for item in items if item.get("expected_answer_type", "graph_positive") != "no_answer"]
    no_answer = [item for item in items if item.get("expected_answer_type") == "no_answer"]
    pmid_labeled = [item for item in graph_positive if item.get("gold_pmids")]
    claim_labeled = [item for item in graph_positive if item.get("gold_claim_ids")]
    external_review = [item for item in graph_positive if not item.get("gold_pmids") and not item.get("gold_claim_ids")]

    summary = {
        "count": len(items),
        "success_rate": round(mean(1.0 if item["success"] else 0.0 for item in items), 4),
        "json_parse_rate": round(mean(1.0 if item["json_parse_success"] else 0.0 for item in items), 4),
        "avg_tool_calls": round(mean(item["tool_call_count"] for item in items), 2),
    }

    if graph_positive:
        summary.update(
            {
                "graph_positive_count": len(graph_positive),
                "primary_metric": "pmid_recall" if pmid_labeled else "external_review_required",
                "pmid_labeled_count": len(pmid_labeled),
                "claim_labeled_count": len(claim_labeled),
                "external_review_count": len(external_review),
            }
        )
        if pmid_labeled:
            summary.update(
                {
                    "pmid_hit": round(mean(item["pmid_hit"] for item in pmid_labeled), 4),
                    "pmid_recall": round(mean(item["pmid_recall"] for item in pmid_labeled), 4),
                }
            )
        if claim_labeled:
            summary.update(
                {
                    "index_self_consistency_claim_hit": round(mean(item["claim_hit"] for item in claim_labeled), 4),
                    "index_self_consistency_claim_recall": round(mean(item["claim_recall"] for item in claim_labeled), 4),
                }
            )

    if no_answer:
        summary.update(
            {
                "no_answer_count": len(no_answer),
                "no_answer_correct": round(
                    mean(1.0 if item.get("no_answer_correct") else 0.0 for item in no_answer),
                    4,
                ),
                "abstention_rate": round(
                    mean(1.0 if item.get("abstained") else 0.0 for item in no_answer),
                    4,
                ),
            }
        )

    by_type = {}
    for qtype in sorted({item["question_type"] for item in items}):
        group = [item for item in items if item["question_type"] == qtype]
        group_summary = {
            "count": len(group),
            "success_rate": round(mean(1.0 if item["success"] else 0.0 for item in group), 4),
            "json_parse_rate": round(mean(1.0 if item["json_parse_success"] else 0.0 for item in group), 4),
        }
        if all(item.get("expected_answer_type", "graph_positive") == "no_answer" for item in group):
            group_summary["no_answer_correct"] = round(
                mean(1.0 if item.get("no_answer_correct") else 0.0 for item in group),
                4,
            )
            group_summary["abstention_rate"] = round(
                mean(1.0 if item.get("abstained") else 0.0 for item in group),
                4,
            )
        else:
            positive_group = [
                item for item in group if item.get("expected_answer_type", "graph_positive") != "no_answer"
            ]
            pmid_group = [item for item in positive_group if item.get("gold_pmids")]
            claim_group = [item for item in positive_group if item.get("gold_claim_ids")]
            external_group = [item for item in positive_group if not item.get("gold_pmids") and not item.get("gold_claim_ids")]
            group_summary.update(
                {
                    "pmid_labeled_count": len(pmid_group),
                    "claim_labeled_count": len(claim_group),
                    "external_review_count": len(external_group),
                }
            )
            if pmid_group:
                group_summary.update(
                    {
                        "pmid_hit": round(mean(item["pmid_hit"] for item in pmid_group), 4),
                        "pmid_recall": round(mean(item["pmid_recall"] for item in pmid_group), 4),
                    }
                )
            if claim_group:
                group_summary.update(
                    {
                        "index_self_consistency_claim_hit": round(mean(item["claim_hit"] for item in claim_group), 4),
                        "index_self_consistency_claim_recall": round(mean(item["claim_recall"] for item in claim_group), 4),
                    }
                )
        by_type[qtype] = group_summary
    summary["by_question_type"] = by_type
    return summary


async def run_items(agent_module, items: list[dict[str, Any]], max_iterations: int) -> list[dict[str, Any]]:
    scored = []
    for idx, item in enumerate(items, start=1):
        print(f"[{idx}/{len(items)}] {item['id']} {item['question_type']}: {item['question']}", flush=True)
        result = await agent_module.query_with_agent_async(item["question"], max_iterations=max_iterations)
        scored_item = score_answer(item, result)
        print(
            json.dumps(
                {
                    "id": scored_item["id"],
                    "success": scored_item["success"],
                    "json": scored_item["json_parse_success"],
                    "claim_hit": scored_item["claim_hit"],
                    "pmid_hit": scored_item["pmid_hit"],
                    "tool_calls": scored_item["tool_call_count"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        scored.append(scored_item)
    return scored


def needs_retry(scored_item: dict[str, Any]) -> bool:
    """An item is worth retrying if the agent failed, produced no parseable JSON,
    or never invoked a tool (empty exploration)."""
    return (
        not scored_item.get("success")
        or not scored_item.get("json_parse_success")
        or scored_item.get("tool_call_count", 0) == 0
    )


async def run_items_with_checkpoint(
    agent_module,
    items: list[dict[str, Any]],
    max_iterations: int,
    item_timeout: float | None,
    output_path: Path,
    payload_base: dict[str, Any],
    retries: int = 0,
) -> list[dict[str, Any]]:
    scored = []
    for idx, item in enumerate(items, start=1):
        print(f"[{idx}/{len(items)}] {item['id']} {item['question_type']}: {item['question']}", flush=True)
        scored_item = None
        for attempt in range(retries + 1):
            try:
                query_coro = agent_module.query_with_agent_async(item["question"], max_iterations=max_iterations)
                if item_timeout and item_timeout > 0:
                    result = await asyncio.wait_for(query_coro, timeout=item_timeout)
                else:
                    result = await query_coro
            except TimeoutError:
                result = {
                    "question": item["question"],
                    "error": f"Timed out after {item_timeout} seconds",
                    "success": False,
                }
            scored_item = score_answer(item, result)
            scored_item["attempts"] = attempt + 1
            if not needs_retry(scored_item):
                break
            if attempt < retries:
                print(f"    retry {attempt + 1}/{retries} for {item['id']} (success={scored_item['success']}, json={scored_item['json_parse_success']}, tool_calls={scored_item['tool_call_count']})", flush=True)
        print(
            json.dumps(
                {
                    "id": scored_item["id"],
                    "success": scored_item["success"],
                    "json": scored_item["json_parse_success"],
                    "claim_hit": scored_item["claim_hit"],
                    "pmid_hit": scored_item["pmid_hit"],
                    "tool_calls": scored_item["tool_call_count"],
                    "attempts": scored_item.get("attempts"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        scored.append(scored_item)
        checkpoint_payload = {
            **payload_base,
            "completed": len(scored),
            "complete": len(scored) == len(items),
            "summary": summarize(scored),
            "items": scored,
        }
        output_path.write_text(
            json.dumps(checkpoint_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return scored


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--max-iterations", type=int, default=8)
    parser.add_argument(
        "--item-timeout",
        type=float,
        default=420,
        help="Maximum seconds to wait for one Agent query before recording a timeout failure.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=0,
        help="Number of extra attempts per item when the agent fails, returns no parseable JSON, or makes no tool calls.",
    )
    args = parser.parse_args()

    benchmark = load_json(args.benchmark)
    items = benchmark["items"][args.offset :]
    if args.limit:
        items = items[: args.limit]

    agent_module = load_agent_module(AGENT_PATH)
    payload = {
        "benchmark_id": benchmark.get("benchmark_id"),
        "benchmark_path": str(args.benchmark),
        "limit": args.limit,
        "offset": args.offset,
        "max_iterations": args.max_iterations,
        "item_timeout": args.item_timeout,
        "retries": args.retries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scored = asyncio.run(
        run_items_with_checkpoint(
            agent_module,
            items,
            args.max_iterations,
            args.item_timeout,
            args.output,
            payload,
            args.retries,
        )
    )
    payload = {
        **payload,
        "completed": len(scored),
        "complete": True,
        "summary": summarize(scored),
        "items": scored,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    print(f"Wrote results to {args.output}")


if __name__ == "__main__":
    main()
