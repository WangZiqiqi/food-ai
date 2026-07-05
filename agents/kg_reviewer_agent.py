#!/usr/bin/env python3
"""
KG Reviewer Agent V2 - translated note,translated note pydantic-ai translated note
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from sdk_runtime import (
    configure_sdk_environment,
    create_debug_options,
    extract_text_and_tool_calls,
    log_stream_event,
)


PROJECT_ROOT = Path(__file__).parent.parent.resolve()
GRAPH_SUMMARY_COMMAND = (
    "uv run python .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/analyze_graph.py "
    "| python -c \"import json,sys; d=json.load(sys.stdin); "
    "print(f'total_nodes={d[\\\"total_nodes\\\"]}'); "
    "print(f'total_edges={d[\\\"total_edges\\\"]}'); "
    "print(f'total_claims={d[\\\"total_claims\\\"]}'); "
    "print('node_stats=' + json.dumps(d['node_stats'], ensure_ascii=False)); "
    "print('top_foods=' + json.dumps(d['foods_top'][:5], ensure_ascii=False)); "
    "print('top_strains=' + json.dumps(d['strains_top'][:5], ensure_ascii=False))\""
)
ISSUE_SUMMARY_COMMAND = (
    "uv run python .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/detect_issues.py "
    "| python -c \"import json,sys; d=json.load(sys.stdin); "
    "print('suspicious_entities=' + json.dumps([x['name'] for x in d.get('suspicious_entities', [])], ensure_ascii=False)); "
    "print('duplicate_candidates=' + json.dumps([[x['entity_a'], x['entity_b']] for x in d.get('duplicate_candidates', [])], ensure_ascii=False)); "
    "print('potential_conflicts=' + json.dumps([[x['subject'], x['object']] for x in d.get('potential_conflicts', [])], ensure_ascii=False))\""
)

try:
    configure_sdk_environment(PROJECT_ROOT)
except RuntimeError as exc:
    print(f"translated note: {exc}", file=sys.stderr)
    sys.exit(1)


def _load_prebuilt_quality_digest() -> str:
    """translated note in-build translated note _quality_report.json,translated note prompt."""
    path = os.environ.get("FOOD_AI_QUALITY_REPORT_PATH")
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return f"(quality_report translated note: {exc})"

    summary = report.get("summary", {})
    over_specific = report.get("over_specific_foods", []) or []
    suspicious = report.get("suspicious_foods", []) or []
    warnings_by_pmid = report.get("warnings_by_pmid", {}) or {}
    top_foods = report.get("top_foods", []) or []
    rec = report.get("review_recommendation", {})

    lines = [
        f"- summary: {json.dumps(summary, ensure_ascii=False)}",
        f"- review_recommendation: {json.dumps(rec, ensure_ascii=False)}",
    ]
    if suspicious:
        lines.append(f"- suspicious_foods ({len(suspicious)}): {json.dumps(suspicious, ensure_ascii=False)}")
    if over_specific:
        lines.append(
            f"- over_specific_foods ({len(over_specific)}): "
            f"{json.dumps(over_specific, ensure_ascii=False)}"
        )
    if top_foods:
        lines.append(f"- top_foods (name, count): {json.dumps(top_foods, ensure_ascii=False)}")
    if warnings_by_pmid:
        sample_pmids = list(warnings_by_pmid.keys())[:8]
        lines.append(
            f"- warnings_by_pmid: {len(warnings_by_pmid)} pmid(s) flagged; "
            f"sample pmids: {sample_pmids}"
        )
    lines.append(f"- source_path: {path}")
    return "\n".join(lines)


async def review_graph_async() -> Dict[str, Any]:
    """translated note KG Reviewer Agent,translated note"""
    try:
        from claude_agent_sdk import ClaudeAgentOptions, query
    except ImportError as e:
        print(f"translated note: translated note claude-agent-sdk: {e}")
        sys.exit(1)

    quality_digest = _load_prebuilt_quality_digest()
    if quality_digest:
        prebuilt_section = (
            "## Pre-Detected Quality Issues (rule-based, from in-build extractor)\n\n"
            "These are issues already flagged by the deterministic build-time quality check. "
            "Treat them as a high-priority input list — every entry should either be addressed "
            "in your Issues Found section with a concrete `Suggested Action`, or explicitly "
            "justified as a false positive.\n\n"
            f"{quality_digest}\n"
        )
    else:
        prebuilt_section = (
            "## Pre-Detected Quality Issues\n\n"
            "(no `FOOD_AI_QUALITY_REPORT_PATH` set — rely on automated detection only)\n"
        )

    prompt = f"""You are the KG Reviewer Agent, an expert in knowledge graph quality assessment.

Your task is to thoroughly review the food-health knowledge graph and identify all quality issues.

## Context

This is a V3 Claim-Centric knowledge graph built from PubMed papers about fermented foods and probiotics.
- The graph being reviewed is whatever artifacts the in-build refine hook (or orchestrator) points to via `FOOD_AI_KG_PICKLE_PATH` / `FOOD_AI_KG_JSON_PATH` env vars. Always inspect that graph, not stale snapshots under older `data/processed/` directories.

{prebuilt_section}
## Your Task

Perform a comprehensive quality review following these steps:

### Step 1: Global Analysis
Use the Bash tool to run:
`{GRAPH_SUMMARY_COMMAND}`

### Step 2: Automated Issue Detection
Use the Bash tool to run:
`{ISSUE_SUMMARY_COMMAND}`

### Step 3: Deep Investigation
For each pre-detected over_specific_food, suspicious_food, and each duplicate/conflict surfaced by `detect_issues.py`:
- Use the Bash tool to run:
  `uv run python .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/get_entity_info.py <entity_name> <entity_type>`
- Use the Read tool to check original papers in `data/raw/{{pmid}}.json` only when strictly necessary
- Decide a concrete action: `merge` to a parent entity, `rename` to a normalized form, `update_type`, `normalize`, `delete_orphan`, or — only with explicit justification — `preserve` / `no_change`

### Step 4: Pattern Analysis
Look for systematic patterns (naming family clusters, abbreviation styles, plural/singular pairs, vitamin-fortified / supplement variants).

## Action Selection Rules (read carefully — affects refiner behavior)

- **For every entity in `over_specific_foods`**, propose a concrete action (`merge` / `rename` / `delete_orphan`). Do not blanket-`preserve`. If you genuinely cannot find a better parent or normalized name after one `get_entity_info.py` call, label it `mark_out_of_scope` rather than `preserve`.
- **For directional conflicts** (same subject + object with opposing `effect_direction`):
  - If both claims come from **different PMIDs** AND have distinct `study_context`/`population`/`dose`, `preserve` IS legitimate — but state the PMIDs and the differing context explicitly.
  - If claims share a PMID, or one has weak/no context evidence, propose `merge` (keep the stronger evidence) or `update_type` (fix the wrong direction). Never default to `preserve` without checking the PMIDs.
- **For naming inconsistencies** (capitalization, separator drift, singular/plural), propose `rename` or `normalize`, not `no_change`.
- **Do not** use `preserve` / `no_change` as a default catch-all. They are valid only with a stated reason that survives scrutiny.

## Important Execution Rules

- Do not start with generic repository exploration.
- First run the summary `analyze_graph.py` pipeline above, then the summary `detect_issues.py` pipeline above.
- Do not run Bash tools in parallel.
- Wait for the tool result from Step 1 before starting Step 2.
- Only inspect extra files after those two commands complete.
- Use the kg-refiner scripts as the primary workflow, not ad-hoc shell exploration.
- Keep the investigation bounded. You are writing a review report, not exhaustively exploring the whole repository.
- Use at most 8 Bash tool calls total.
- After Step 1 and Step 2, investigate at most 5 concrete issue groups (prioritise over_specific_foods and detect_issues.py output).
- Prefer the issues already surfaced by the Pre-Detected list and by `detect_issues.py`; do not branch into broad exploratory searches.
- Do not inspect unrelated large JSON files unless they are strictly necessary to verify one specific issue.
- Once you have enough evidence for a useful report, stop tool use and write the final review immediately.
- Do not send issues to a human/manual branch. This loop must handle them.
- If an issue should not be auto-modified, classify it as `mark_out_of_scope` (clearly external scope) or `preserve` (with PMID-level justification). Avoid `no_change` unless it is truly a non-issue.

## Output Format (Natural Language)

Please output your findings in natural language with clear sections:

---

## Review Summary

Total nodes: [number]
Total claims: [number]
Overall health: [good/fair/poor]

Critical issues: [count]
Major issues: [count]
Minor issues: [count]

## Issues Found

### ISSUE-001: [Type] - [Entity Name]

- **Severity**: [critical/major/minor]
- **Entity**: [name] ([type])
- **Current State**: [description of problem]
- **Expected State**: [what it should be]
- **Evidence**: [how you discovered this]
- **PMIDs Affected**: [list of pmids]
- **Suggested Action**: [merge/rename/normalize/update_type/delete_orphan/mark_out_of_scope/preserve/no_change]
- **Confidence**: [high/medium/low]

[Repeat for each issue...]

## Patterns Identified

[Describe any systematic patterns you found]

## Statistics

- Misclassifications: [count]
- Duplicates: [count]
- Over-specific variants: [count]
- Conflicts: [count]
- Naming issues: [count]

---

Be thorough and specific. Use the tools to verify your findings."""

    print(" translated note KG Reviewer Agent...")
    print(f"   translated note: {PROJECT_ROOT}")

    try:
        debug_enabled = os.environ.get("FOOD_AI_AGENT_DEBUG", "").lower() in {
            "1",
            "true",
            "yes",
        }
        debug_options, debug_state = create_debug_options(debug_enabled)

        options = ClaudeAgentOptions(
            cwd=str(PROJECT_ROOT),
            permission_mode="bypassPermissions",
            add_dirs=[str(PROJECT_ROOT / ".agent-skills" / "kg-refiner")],
            max_turns=40,
            **debug_options,
        )

        response_stream = query(prompt=prompt, options=options)

        full_response: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        event_counts: dict[str, int] = {}
        last_event_type: str | None = None
        last_result_payload: dict[str, Any] | None = None
        async for event in response_stream:
            event_type = type(event).__name__
            if getattr(event, "session_id", None) and not debug_state.get("session_id"):
                debug_state["session_id"] = getattr(event, "session_id")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            last_event_type = event_type
            if event_type == "ResultMessage":
                last_result_payload = {
                    "result": getattr(event, "result", None),
                    "stop_reason": getattr(event, "stop_reason", None),
                    "subtype": getattr(event, "subtype", None),
                    "is_error": getattr(event, "is_error", None),
                    "num_turns": getattr(event, "num_turns", None),
                }
            texts, event_tool_calls = extract_text_and_tool_calls(event)
            if debug_enabled:
                log_stream_event(event, texts, event_tool_calls, debug_state)
            full_response.extend(texts)
            tool_calls.extend(event_tool_calls)

        result_subtype = (last_result_payload or {}).get("subtype")
        result_incomplete = isinstance(result_subtype, str) and result_subtype.startswith("error_")
        error_message = None
        if result_incomplete:
            error_message = (
                f"Reviewer stopped before producing a final report: "
                f"subtype={result_subtype}, stop_reason={(last_result_payload or {}).get('stop_reason')}"
            )

        return {
            "agent_response": "".join(full_response),
            "tool_calls": tool_calls,
            "event_counts": event_counts,
            "last_event_type": last_event_type,
            "last_result_payload": last_result_payload,
            "error": error_message,
            "session_id": debug_state.get("session_id"),
            "transcript_paths": debug_state.get("transcript_paths", []),
            "success": not result_incomplete,
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def review_graph() -> Dict[str, Any]:
    """Synchronous wrapper"""
    return asyncio.run(review_graph_async())


def main() -> None:
    print("=" * 70)
    print("KG Reviewer Agent V2 - translated note")
    print("=" * 70)
    print()

    result = review_graph()

    if not result.get("success"):
        print(f"\n translated note: {result.get('error')}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("translated note")
    print("=" * 70)

    output_file = Path("data/kg_reviewer_v2_raw.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\ntranslated note: {output_file}")

    if result.get("session_id"):
        print(f"Session ID: {result['session_id']}")
    if result.get("transcript_paths"):
        print("Transcript paths:")
        for path in result["transcript_paths"]:
            print(f"  - {path}")

    response = result.get("agent_response", "")
    print("\n translated note (translated note1000translated note):")
    print("-" * 70)
    print(response[:1000] + "..." if len(response) > 1000 else response)


if __name__ == "__main__":
    main()
