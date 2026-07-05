#!/usr/bin/env python3
"""Analyze saved Query Agent tool calls from benchmark result JSON."""

from __future__ import annotations

import argparse
import json
import shlex
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any


DEFAULT_INPUT = Path(
    "data/evaluation/query_benchmark_850_agent_answer_results_clean_120_plus_no_answer_25_combined.json"
)
DEFAULT_OUTPUT = Path("data/evaluation/query_benchmark_850_agent_tool_call_analysis.md")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def command_from_call(call: dict[str, Any]) -> str | None:
    if call.get("name") != "Bash":
        return None
    payload = call.get("input") or {}
    command = payload.get("command") if isinstance(payload, dict) else None
    return command if isinstance(command, str) else None


def script_name(command: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    for part in parts:
        if part.endswith(".py"):
            return Path(part).name
    return "unknown"


def command_query(command: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    for idx, part in enumerate(parts):
        if part.endswith(".py") and idx + 1 < len(parts):
            next_part = parts[idx + 1]
            if not next_part.startswith("-"):
                return next_part
    return ""


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


def analyze_item(item: dict[str, Any]) -> dict[str, Any]:
    commands = [command for call in item.get("tool_calls", []) if (command := command_from_call(call))]
    script_counts = Counter(script_name(command) for command in commands)
    command_counts = Counter(commands)
    repeated_commands = {command: count for command, count in command_counts.items() if count > 1}
    query_counts = Counter((script_name(command), command_query(command)) for command in commands)
    repeated_queries = {
        f"{script}: {query}": count
        for (script, query), count in query_counts.items()
        if query and count > 1
    }
    return {
        "id": item["id"],
        "question_type": item["question_type"],
        "question": item["question"],
        "tool_call_count": item["tool_call_count"],
        "bash_calls": len(commands),
        "tool_result_calls": sum(1 for call in item.get("tool_calls", []) if call.get("name") == "tool_result"),
        "script_counts": dict(script_counts),
        "unique_commands": len(command_counts),
        "repeated_command_count": sum(count - 1 for count in command_counts.values() if count > 1),
        "repeated_commands": repeated_commands,
        "repeated_query_count": sum(count - 1 for count in query_counts.values() if count > 1),
        "repeated_queries": repeated_queries,
    }


def generate_report(payload: dict[str, Any], top_n: int, focus_ids: set[str]) -> str:
    items = payload["items"]
    analyses = [analyze_item(item) for item in items]
    tool_counts = [item["tool_call_count"] for item in items]

    script_totals = Counter()
    for analysis in analyses:
        script_totals.update(analysis["script_counts"])

    by_type = {}
    for qtype in sorted({item["question_type"] for item in items}):
        group = [item for item in items if item["question_type"] == qtype]
        values = [item["tool_call_count"] for item in group]
        by_type[qtype] = {
            "count": len(group),
            "avg": mean(values),
            "median": median(values),
            "max": max(values),
        }

    lines = [
        "# Query Agent Tool-Call Analysis",
        "",
        f"Input: `{payload.get('benchmark_path', DEFAULT_INPUT)}`",
        "",
        "## Overall",
        "",
        md_table(
            ["Count", "Avg tool calls", "Median", "P90", "Max"],
            [
                [
                    len(tool_counts),
                    f"{mean(tool_counts):.2f}",
                    median(tool_counts),
                    sorted(tool_counts)[int(len(tool_counts) * 0.9) - 1],
                    max(tool_counts),
                ]
            ],
        ),
        "",
        "## By Question Type",
        "",
        md_table(
            ["Question type", "Count", "Avg", "Median", "Max"],
            [
                [qtype, stats["count"], f"{stats['avg']:.2f}", stats["median"], stats["max"]]
                for qtype, stats in by_type.items()
            ],
        ),
        "",
        "## Script Usage",
        "",
        md_table(
            ["Script", "Bash calls"],
            [[script, count] for script, count in script_totals.most_common()],
        ),
        "",
        f"## Top {top_n} Cost Cases",
        "",
        md_table(
            ["Case", "Type", "Tool calls", "Bash calls", "Unique commands", "Repeated commands", "Question"],
            [
                [
                    analysis["id"],
                    analysis["question_type"],
                    analysis["tool_call_count"],
                    analysis["bash_calls"],
                    analysis["unique_commands"],
                    analysis["repeated_command_count"],
                    analysis["question"],
                ]
                for analysis in sorted(analyses, key=lambda row: row["tool_call_count"], reverse=True)[:top_n]
            ],
        ),
        "",
        "## Focus Cases",
        "",
    ]

    by_id = {analysis["id"]: analysis for analysis in analyses}
    for case_id in sorted(focus_ids):
        analysis = by_id.get(case_id)
        if not analysis:
            continue
        lines.extend(
            [
                f"### {case_id}",
                "",
                f"- Type: `{analysis['question_type']}`",
                f"- Tool calls: `{analysis['tool_call_count']}`",
                f"- Bash calls: `{analysis['bash_calls']}`",
                f"- Unique commands: `{analysis['unique_commands']}`",
                f"- Repeated command overhead: `{analysis['repeated_command_count']}`",
                f"- Repeated query overhead: `{analysis['repeated_query_count']}`",
                "",
                "Script mix:",
                "",
                md_table(
                    ["Script", "Calls"],
                    [[script, count] for script, count in Counter(analysis["script_counts"]).most_common()],
                ),
                "",
            ]
        )
        if analysis["repeated_queries"]:
            lines.extend(
                [
                    "Repeated queries:",
                    "",
                    md_table(
                        ["Query", "Count"],
                        [[query, count] for query, count in analysis["repeated_queries"].items()],
                    ),
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument(
        "--focus-id",
        action="append",
        default=["qa850_049", "qa850_039", "qa850_040", "qa850_na_003"],
    )
    args = parser.parse_args()

    payload = load_json(args.input)
    report = generate_report(payload, args.top_n, set(args.focus_id))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote report to {args.output}")


if __name__ == "__main__":
    main()
