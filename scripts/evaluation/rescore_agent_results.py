#!/usr/bin/env python3
"""Rescore existing Agent benchmark outputs against an updated benchmark file.

This is useful when benchmark labels/gold IDs are corrected without needing to
rerun expensive Agent calls.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_runner_module():
    path = Path("scripts/evaluation/run_agent_answer_benchmark.py")
    spec = importlib.util.spec_from_file_location("run_agent_answer_benchmark", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def detects_abstention(module, answer_data: dict[str, Any] | None, raw_text: str) -> bool:
    return module.detects_abstention(answer_data, raw_text)


def extract_json_object(module, raw_text: str) -> dict[str, Any] | None:
    return module.extract_json_object(raw_text)


def extract_pmids_from_item(item: dict[str, Any]) -> set[str]:
    values = item.get("predicted_pmids")
    if values is not None:
        return {str(value) for value in values}
    raw = item.get("raw_agent_response", "") or ""
    return set(re.findall(r"\bPMID[:\s]*(\d{6,9})\b", raw, re.IGNORECASE))


def extract_claims_from_item(item: dict[str, Any]) -> set[str]:
    values = item.get("predicted_claim_ids")
    if values is not None:
        return {str(value) for value in values}
    raw = item.get("raw_agent_response", "") or ""
    return set(re.findall(r"\b[0-9a-f]{12}\b", raw))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--note", default="Existing Agent outputs rescored against updated benchmark labels/gold.")
    args = parser.parse_args()

    module = load_runner_module()
    benchmark = load_json(args.benchmark)
    results = load_json(args.results)
    benchmark_items = {item["id"]: item for item in benchmark["items"]}

    for item in results["items"]:
        bench_item = benchmark_items[item["id"]]
        raw = item.get("raw_agent_response", "") or ""
        parsed = item.get("answer_data") or extract_json_object(module, raw)
        predicted_claims = extract_claims_from_item(item)
        predicted_pmids = extract_pmids_from_item(item)
        gold_claims = set(bench_item.get("gold_claim_ids", []))
        gold_pmids = {str(pmid) for pmid in bench_item.get("gold_pmids", [])}
        expected_answer_type = bench_item.get("expected_answer_type", "graph_positive")
        no_answer_expected = module.is_no_answer_item(bench_item)
        abstained = detects_abstention(module, parsed, raw)
        claim_hits = predicted_claims & gold_claims
        pmid_hits = predicted_pmids & gold_pmids

        item["question_type"] = bench_item.get("question_type", item.get("question_type"))
        item["expected_answer_type"] = expected_answer_type
        item["external_review"] = bench_item.get("external_review")
        item["gold_claim_ids_original_result"] = item.get("gold_claim_ids", [])
        item["gold_pmids_original_result"] = item.get("gold_pmids", [])
        item["gold_claim_ids"] = sorted(gold_claims)
        item["gold_pmids"] = sorted(gold_pmids)
        item["abstained"] = abstained
        item["claim_hit"] = None if no_answer_expected or not gold_claims else (1.0 if claim_hits else 0.0)
        item["claim_recall"] = None if no_answer_expected or not gold_claims else len(claim_hits) / len(gold_claims)
        item["pmid_hit"] = None if no_answer_expected or not gold_pmids else (1.0 if pmid_hits else 0.0)
        item["pmid_recall"] = None if no_answer_expected or not gold_pmids else len(pmid_hits) / len(gold_pmids)
        item["no_answer_correct"] = (
            abstained and not claim_hits and not pmid_hits if no_answer_expected else None
        )

    results["benchmark_id"] = benchmark.get("benchmark_id")
    results["benchmark_path"] = str(args.benchmark)
    results["rescore_note"] = args.note
    results["summary"] = module.summarize(results["items"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results["summary"], ensure_ascii=False, indent=2))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
