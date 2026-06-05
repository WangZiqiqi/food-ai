#!/usr/bin/env python3
"""Summarize the final Food-AI graph/evaluation bundle into Markdown tables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

MANIFEST = Path("data/evaluation/manifests/food_ai_final_manifest.json")


def fmt(value):
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(fmt(x) for x in row) + " |")
    return "\n".join(lines)


def generate(manifest_path: Path = MANIFEST) -> str:
    manifest = json.loads(manifest_path.read_text())
    summaries = manifest["summaries"]
    quality = summaries["quality"]
    retrieval = summaries["clean120_retrieval"]
    agent = summaries["clean120_agent"]
    independent = summaries["independent_agent"]
    raw = summaries["raw_abstract_baseline"]

    sections = [
        "# Food-AI Experiment Tables",
        "",
        "Generated from the final 850-paper graph/evaluation manifest.",
        "",
        "## Corpus and Graph Scale",
        md_table(
            ["Artifact", "Articles", "Success", "Errors", "Merged claims", "Zero-claim articles", "Over-specific foods"],
            [[
                "850-paper final graph",
                quality["articles_total"],
                quality["articles_success"],
                quality["articles_error"],
                quality["merged_claims"],
                quality["zero_claim_articles"],
                quality["over_specific_food_entities"],
            ]],
        ),
        "",
        "## Retrieval Evaluation on Repaired Clean 120",
        md_table(
            ["Setting", "PMID hit@10", "PMID recall@10", "PMID recall@20", "Claim hit@10", "Claim recall@10", "MRR"],
            [[
                "Claim vectors, natural question",
                retrieval["primary_pmid_metrics"]["pmid_hit@10"],
                retrieval["primary_pmid_metrics"]["pmid_recall@10"],
                retrieval["primary_pmid_metrics"]["pmid_recall@20"],
                retrieval["index_self_consistency"]["claim_hit@10"],
                retrieval["index_self_consistency"]["claim_recall@10"],
                retrieval["index_self_consistency"]["mrr"],
            ]],
        ),
        "",
        "## Full Agent Evaluation on Repaired Clean 120",
        md_table(
            ["Count", "Success rate", "JSON parse rate", "PMID hit", "PMID recall", "Avg. tool calls"],
            [[
                agent["count"],
                agent["success_rate"],
                agent["json_parse_rate"],
                agent["pmid_hit"],
                agent["pmid_recall"],
                agent["avg_tool_calls"],
            ]],
        ),
        "",
        "## Independent v1 Evaluation",
        md_table(
            ["Count", "Graph-positive", "No-answer", "No-answer correct", "Abstention rate", "PMID recall (labeled subset)"],
            [[
                independent["count"],
                independent["graph_positive_count"],
                independent["no_answer_count"],
                independent["no_answer_correct"],
                independent["abstention_rate"],
                independent["pmid_recall"],
            ]],
        ),
        "",
        "## Raw Abstract Document Vector Baseline",
        md_table(
            ["Setting", "PMID hit@10", "PMID recall@10", "PMID hit@20", "PMID recall@20", "False abstention"],
            [[
                "Raw abstract natural top-20",
                raw["pmid_hit@10"],
                raw["pmid_recall@10"],
                raw["pmid_hit@20"],
                raw["pmid_recall@20"],
                raw["false_abstention_rate"],
            ]],
        ),
        "",
    ]
    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    content = generate(args.manifest)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n")
    else:
        print(content)


if __name__ == "__main__":
    main()
