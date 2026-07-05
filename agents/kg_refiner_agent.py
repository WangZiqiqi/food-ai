#!/usr/bin/env python3
"""
KG Refiner Agent - translated note
translated note Claude Agent SDK translated note
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from sdk_runtime import (
    configure_sdk_environment,
    create_debug_options,
    extract_text_and_tool_calls,
    log_stream_event,
)

PROJECT_ROOT = Path(__file__).parent.parent.resolve()  # translated note agents/ translated note
try:
    configure_sdk_environment(PROJECT_ROOT)
except RuntimeError as exc:
    print(f"translated note: {exc}", file=sys.stderr)
    sys.exit(1)

PYTHON_BIN = sys.executable
GRAPH_SUMMARY_COMMAND = (
    f"{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/analyze_graph.py "
    "| python -c \"import json,sys; d=json.load(sys.stdin); "
    "print(f'total_nodes={d[\\\"total_nodes\\\"]}'); "
    "print(f'total_edges={d[\\\"total_edges\\\"]}'); "
    "print(f'total_claims={d[\\\"total_claims\\\"]}'); "
    "print('node_stats=' + json.dumps(d['node_stats'], ensure_ascii=False)); "
    "print('top_foods=' + json.dumps(d['foods_top'][:5], ensure_ascii=False)); "
    "print('top_strains=' + json.dumps(d['strains_top'][:5], ensure_ascii=False))\""
)
ISSUE_SUMMARY_COMMAND = (
    f"{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/detect_issues.py "
    "| python -c \"import json,sys; d=json.load(sys.stdin); "
    "print('suspicious_entities=' + json.dumps([x['name'] for x in d.get('suspicious_entities', [])], ensure_ascii=False)); "
    "print('duplicate_candidates=' + json.dumps([[x['entity_a'], x['entity_b']] for x in d.get('duplicate_candidates', [])], ensure_ascii=False)); "
    "print('potential_conflicts=' + json.dumps([[x['subject'], x['object']] for x in d.get('potential_conflicts', [])], ensure_ascii=False))\""
)


async def refine_graph_async():
    """translated note KG Refiner Agent"""
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError as e:
        print(f"translated note: translated note claude-agent-sdk: {e}")
        sys.exit(1)

    prompt = f"""You are the KG Refiner Agent, an expert in knowledge graph quality improvement.

Your task is to analyze and improve the quality of a food-health knowledge graph.

## Context

This is a V3 claim-centric knowledge graph built from 850 PubMed records about fermented foods and probiotics.
The frozen public graph has 6,963 nodes (3,786 claims and 3,177 entity nodes) and 7,572 edges.

Known quality-review targets:
- Some entities may be duplicates or near-duplicates.
- Some entities may be overly specific food/formulation variants.
- Some claims may need inspection for graph-relative evidence gaps or ambiguous health interpretation.

## Your Task

1. **Analyze the graph** using available tools to understand its structure and identify issues
2. **Detect problems**: suspicious entities, duplicates, potential conflicts
3. **Investigate specific issues** by examining entity details
4. **Propose and execute fixes** (merge duplicates, rename misclassified entities)
5. **Verify improvements** after modifications

## Available Tools (invoke via Bash tool)

### Analysis Tools
```bash
# Get overall graph statistics
{GRAPH_SUMMARY_COMMAND}

# Detect potential issues
{ISSUE_SUMMARY_COMMAND}

# Get detailed info about a specific entity
{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/get_entity_info.py <entity_name> <entity_type>
```

### Modification Tools (auto-backup before changes)
```bash
# Merge two entities into the canonical `target_name`.
# Semantics: `target_name` is the FINAL surviving name. Whichever of entity_a / entity_b
# does NOT match `target_name` will be deleted; its claims are transferred to target_name.
# Example — to consolidate the over-specific `probiotic_supplement_capsule` (10 claims)
# into the cleaner `probiotic_supplement` (1 claim):
#   modify_graph.py merge probiotic_supplement probiotic_supplement_capsule probiotic_supplement food
# (target_name = probiotic_supplement -> probiotic_supplement_capsule is removed.)
{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py merge <entity_a> <entity_b> <target_name> [type]

# Rename an entity (updates all related claims)
{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py rename <old_name> <new_name> <type>

# Retype an entity while preserving connected claims
{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py retype <entity_name> <old_type> <new_type>

# Delete an orphan entity only when it has no connected claims
{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py delete_orphan <entity_name> <type>

# Change only the display name while preserving node id and edges
{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py set_name <entity_name> <type> <display_name>

# Mark a connected but out-of-scope entity without deleting evidence
{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py mark_out_of_scope <entity_name> <type> [reason]
```

## Important Rules

1. **Always analyze first, then act** - Don't make changes without understanding the impact
2. **One change at a time** - Verify each modification before proceeding
3. **Check claim counts** - Entities with many claims need careful handling
4. **Prefer merge over delete** - Keep claims when possible
5. **Document everything** - Report what you found and what you changed
6. **Use the summary analyze command first** - Avoid running the raw full `analyze_graph.py` output unless absolutely necessary
7. **Run Bash tools sequentially** - Wait for each tool result before starting the next one
8. **Verify modify_graph.py output** - Every modify_graph.py call returns JSON. Before reporting `result: "success"` for any action, you MUST inspect that JSON and confirm it contains `"success": true`. If the JSON has `"success": false`, the action FAILED — record `result: "failed"` and include the script's `error` string in `details`. Do not claim success on a failed call.

## Expected Output

Provide a structured report in this JSON format:

```json
{{
  "analysis_summary": "Brief overview of what you found",
  "issues_identified": [
    {{
      "type": "suspicious_entity|duplicate|over_specific|conflict",
      "description": "What the issue is",
      "entities_involved": ["..."],
      "recommended_action": "merge|rename|mark_review|ignore"
    }}
  ],
  "actions_taken": [
    {{
      "action": "merge|rename",
      "details": "What was changed",
      "backup_file": "path to backup",
      "claims_affected": N
    }}
  ],
  "final_assessment": "Quality improvement summary"
}}
```

Begin by analyzing the graph structure and identifying the most significant issues to address."""

    print(" translated note KG Refiner Agent...")
    print(f"   translated note: {PROJECT_ROOT}")
    print("   translated note: food_ai_graph.pkl")

    try:
        debug_enabled = os.environ.get("FOOD_AI_AGENT_DEBUG", "").lower() in {
            "1",
            "true",
            "yes",
        }
        debug_options, debug_state = create_debug_options(debug_enabled)

        options = ClaudeAgentOptions(
            cwd=str(PROJECT_ROOT),
            permission_mode='bypassPermissions',
            add_dirs=[str(PROJECT_ROOT / ".agent-skills" / "kg-refiner")],
            max_turns=32,
            **debug_options,
        )

        response_stream = query(prompt=prompt, options=options)

        full_response = []
        tool_calls = []
        event_counts = {}
        last_event_type = None
        last_result_payload = None
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

        return {
            "agent_response": "".join(full_response),
            "tool_calls": tool_calls,
            "event_counts": event_counts,
            "last_event_type": last_event_type,
            "last_result_payload": last_result_payload,
            "session_id": debug_state.get("session_id"),
            "transcript_paths": debug_state.get("transcript_paths", []),
            "success": not result_incomplete,
            "error": (
                f"Refiner stopped before producing a final report: "
                f"subtype={result_subtype}, stop_reason={(last_result_payload or {}).get('stop_reason')}"
                if result_incomplete else None
            ),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "success": False
        }


def refine_graph():
    """Synchronous wrapper"""
    return asyncio.run(refine_graph_async())


def main():
    print("=" * 70)
    print("KG Refiner Agent - translated note")
    print("=" * 70)
    print()

    result = refine_graph()

    if not result.get("success"):
        print(f"\n translated note: {result.get('error')}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("Agent translated note")
    print("=" * 70)

    response = result.get("agent_response", "")

    # Try to extract JSON output
    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)

    if json_match:
        try:
            report = json.loads(json_match.group(1))
            print("\n translated note:")
            print(f"\ntranslated note: {report.get('analysis_summary', 'N/A')}")

            issues = report.get('issues_identified', [])
            print(f"\ntranslated note {len(issues)} translated note:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. [{issue.get('type')}] {issue.get('description')}")
                print(f"     translated note: {issue.get('recommended_action')}")

            actions = report.get('actions_taken', [])
            print(f"\ntranslated note {len(actions)} translated note:")
            for action in actions:
                print(f"  - {action.get('action')}: {action.get('details')}")
                print(f"    translated note {action.get('claims_affected', 0)} translated note claims")

            print(f"\ntranslated note: {report.get('final_assessment', 'N/A')}")

        except json.JSONDecodeError:
            print("\nWarning:  translated note JSON translated note,translated note:")
            print(response[-3000:] if len(response) > 3000 else response)
    else:
        print("\nAgent translated note:")
        print("-" * 70)
        print(response[-3000:] if len(response) > 3000 else response)
        print("-" * 70)

    # Save full result
    output_file = Path("data/kg_refiner_result.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\ntranslated note: {output_file}")
    if result.get("session_id"):
        print(f"Session ID: {result['session_id']}")
    if result.get("transcript_paths"):
        print("Transcript paths:")
        for path in result["transcript_paths"]:
            print(f"  - {path}")


if __name__ == "__main__":
    main()


def refine_graph_with_issues(review_report: dict, issue_ids: list) -> dict:
    """
    translated note(translated note orchestrator translated note)
    """
    import asyncio

    # translated note review_report translated note issues
    all_issues = review_report.get("issues", [])
    issues_to_fix = [i for i in all_issues if i.get("issue_id") in issue_ids]

    if not issues_to_fix:
        return {
            "success": True,
            "message": "No issues to fix",
            "actions_taken": []
        }

    # translated note issues translated note prompt
    prompt = _build_refinement_prompt(issues_to_fix)

    # translated note
    return asyncio.run(_refine_with_prompt_async(prompt))


def _build_refinement_prompt(issues: list) -> str:
    """translated note issue translated note prompt"""

    prompt = """You are the KG Refiner Agent. Fix the following specific issues in the knowledge graph.

## Issues to Fix

"""
    for issue in issues:
        prompt += f"""
### {issue.get('issue_id', 'N/A')}
- Type: {issue.get('type', 'N/A')}
- Severity: {issue.get('severity', 'N/A')}
- Entity: {issue.get('entity_name', 'N/A')} ({issue.get('entity_type', 'N/A')})
- Current: {issue.get('current_state', 'N/A')}
- Expected: {issue.get('expected_state', 'N/A')}
- Action: {issue.get('suggested_action', 'N/A')}
- PMIDs: {', '.join(issue.get('pmids_affected', []))}
"""

    prompt += """
## Your Task

For each issue:
1. Verify with get_entity_info or Read original paper
2. Execute the suggested action using modify_graph
3. Verify the fix
4. Document the action

## Output Format

```json
{
  "analysis_summary": "Brief summary",
  "issues_fixed": [
    {
      "issue_id": "ISSUE-001",
      "action_taken": "merge|rename|delete",
      "result": "success|failed",
      "details": "What was done"
    }
  ]
}
```
"""
    return prompt


async def _refine_with_prompt_async(prompt: str) -> dict:
    """translated note prompt translated note"""
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError as e:
        return {"success": False, "error": f"Cannot import: {e}"}

    debug_enabled = os.environ.get("FOOD_AI_AGENT_DEBUG", "").lower() in {
        "1",
        "true",
        "yes",
    }
    debug_options, debug_state = create_debug_options(debug_enabled)

    options = ClaudeAgentOptions(
        cwd=str(PROJECT_ROOT),
        permission_mode='bypassPermissions',
        add_dirs=[str(PROJECT_ROOT / ".agent-skills" / "kg-refiner")],
        max_turns=32,
        **debug_options,
    )

    try:
        response_stream = query(prompt=prompt, options=options)
        full_response = []
        tool_calls = []
        event_counts = {}
        last_event_type = None
        last_result_payload = None
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

        return {
            "success": not result_incomplete,
            "agent_response": "".join(full_response),
            "tool_calls": tool_calls,
            "event_counts": event_counts,
            "last_event_type": last_event_type,
            "last_result_payload": last_result_payload,
            "session_id": debug_state.get("session_id"),
            "transcript_paths": debug_state.get("transcript_paths", []),
            "error": (
                f"Refiner stopped before producing a final report: "
                f"subtype={result_subtype}, stop_reason={(last_result_payload or {}).get('stop_reason')}"
                if result_incomplete else None
            ),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def refine_graph_with_context_async(review_raw: str, structured_issues: list, issue_ids: list) -> dict:
    """
    translated note(translated note)

    Args:
        review_raw: Reviewer Agent translated note
        structured_issues: translated note issues translated note
        issue_ids: translated note issue_id translated note
    """
    if not structured_issues:
        return {
            "success": True,
            "message": "No issues to fix",
            "actions_taken": []
        }

    # translated note issues translated note prompt,translated note
    prompt = _build_contextual_refinement_prompt(review_raw, structured_issues, issue_ids)

    # translated note
    return await _refine_with_prompt_async(prompt)


async def refine_graph_from_review_async(review_raw: str) -> dict:
    """
    translated note reviewer translated note,translated note issue schema.
    """
    prompt = f"""You are the KG Refiner Agent.

You have received a full review report describing issues in the knowledge graph.
Your job is to perform only safe, tool-supported fixes using the existing kg-refiner workflow.

## Full Review Report

{review_raw[:8000]}

## Allowed Workflow

You may only use these existing commands via the Bash tool:

1. Inspect graph summary:
`{GRAPH_SUMMARY_COMMAND}`

2. Detect issues:
`{ISSUE_SUMMARY_COMMAND}`

3. Inspect one entity:
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/get_entity_info.py <entity_name> <entity_type>`

4. Apply one fix:
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py merge <entity_a> <entity_b> <target_name> [type]`
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py rename <old_name> <new_name> <type>`
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py retype <entity_name> <old_type> <new_type>`
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py delete_orphan <entity_name> <type>`
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py set_name <entity_name> <type> <display_name>`
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py mark_out_of_scope <entity_name> <type> [reason]`

## Hard Constraints

- Do NOT create, edit, or run any new Python script.
- Do NOT use Write, Edit, or here-doc code generation to invent helper scripts.
- Do NOT explore unrelated repository files.
- Do NOT inspect large data files unless strictly necessary.
- Do NOT modify anything unless the review report gives enough evidence that the action is safe.
- Prefer no change over risky change.
- Use at most 12 Bash tool calls total. Budget roughly 2 calls per candidate (1 optional verify + 1 execute). A run that only verifies and never calls `modify_graph.py` is a failure.

## Refinement Policy

- Do not push issues to a human branch. This loop should handle them as far as current tooling allows.
- If the review suggests "keep separate", handle that by preserving entities and optionally applying safer normalization elsewhere.
- If the review suggests hierarchy or variant relationships but current tooling only supports merge/rename, choose the safest concrete action available and explain it.
- If a conflict claim should be preserved, treat that as an intentional no-op within the loop and report it explicitly instead of escalating to human review.
- Never say "manual review required". Use `skip`, `preserve`, or `no_change` within the loop instead.

## Goal

Decide whether there are any safe automatic fixes in the report.
If yes, apply only those fixes using `modify_graph.py`.
If no, explicitly say that no safe automatic fix was applied.

## Output Format

```json
{{
  "analysis_summary": "Brief summary",
  "issues_considered": ["..."],
  "actions_taken": [
    {{
      "action": "merge|rename|retype|delete_orphan|set_name|mark_out_of_scope|normalize|skip",
      "details": "What was changed or why skipped",
      "result": "success|skipped|failed"
    }}
  ],
  "final_assessment": "What changed and what remains manual"
}}
```
"""
    return await _refine_with_prompt_async(prompt)


async def refine_graph_from_candidates_async(review_raw: str, candidates: list[dict]) -> dict:
    """
    translated note reviewer translated note typed refine candidates translated note.
    """
    if not candidates:
        return {
            "success": True,
            "message": "No typed refine candidates were extracted from the review report",
            "agent_response": "",
            "actions_taken": [],
        }

    candidate_text = json.dumps(candidates, indent=2, ensure_ascii=False)
    prompt = f"""You are the KG Refiner Agent.

You are given a review report and a small list of typed refine candidates.
Only work on the candidates below. Do not broaden scope beyond them.

## Review Context

{review_raw[:4000]}

## Typed Refine Candidates

```json
{candidate_text}
```

## Allowed Workflow

You may only use these existing commands via the Bash tool:

1. Inspect graph summary:
`{GRAPH_SUMMARY_COMMAND}`

2. Detect issues:
`{ISSUE_SUMMARY_COMMAND}`

3. Inspect one entity:
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/get_entity_info.py <entity_name> <entity_type>`

4. Apply one fix:
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py merge <entity_a> <entity_b> <target_name> [type]`
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py rename <old_name> <new_name> <type>`
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py retype <entity_name> <old_type> <new_type>`
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py delete_orphan <entity_name> <type>`
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py set_name <entity_name> <type> <display_name>`
`{PYTHON_BIN} .agent-skills/kg-refiner/.claude/skills/kg-refiner/scripts/modify_graph.py mark_out_of_scope <entity_name> <type> [reason]`

## Hard Constraints

- Verification is OPTIONAL: only verify a candidate (via `get_entity_info.py`) when its identity is genuinely ambiguous. If the issue text already names a clear `entity_name (type)` with a clear suggested_action, EXECUTE directly via `modify_graph.py` — do not pre-verify.
- Your goal is APPLYING SAFE FIXES, not verifying. A run that only inspects entities and never calls `modify_graph.py` is a failure.
- Budget guidance: roughly 2 Bash calls per candidate (≤1 optional verify + 1 execute). For N candidates you may use up to `2*N + 2` Bash calls total, but DO NOT spend two verifications on the same candidate — if one verify is not enough to decide, mark it `preserve` / `skip` and move on.
- If a candidate is not clearly safe with current tools, mark it as `preserve`, `skip`, or `no_change` AFTER you have processed (executed or explicitly skipped) the clearly-safe ones first.
- Do not create new scripts.
- Do not inspect unrelated files.
- Prefer doing fewer safe changes over many risky changes — but a "safe change you chose not to execute" still counts as a regression, not safety.

## Merge Semantics (READ — past mistakes here broke the graph)

`modify_graph.py merge <entity_a> <entity_b> <target_name> <type>`:
- `target_name` is the FINAL surviving canonical name.
- Whichever of `entity_a` / `entity_b` does NOT match `target_name` will be DELETED; its claims are transferred to `target_name`.
- To consolidate an over-specific entity X into a cleaner canonical entity Y, pass: `merge Y X Y <type>`.
  Example — fold `probiotic_supplement_capsule` (over-specific, many claims) into `probiotic_supplement` (canonical):
  `modify_graph.py merge probiotic_supplement probiotic_supplement_capsule probiotic_supplement food`
- NEVER pass the over-specific name as `target_name` when your intent is to clean it up.

## Tool Output Verification (CRITICAL)

Every `modify_graph.py` call prints a JSON object. Before you record `result: "success"` for an action you MUST:
1. Locate the JSON in the tool_result.
2. Confirm `"success": true` literally appears in the JSON.
3. If `"success": false`, the action FAILED. Record `result: "failed"` and put the script's `error` string in `details`. Do NOT downstream report success.
Common failure modes you must respect: `delete_orphan` refuses when an entity still has connected claims; merge errors when neither entity exists; rename errors when the target name already exists.

## Output Format

```json
{{
  "analysis_summary": "Brief summary",
  "candidates_received": {len(candidates)},
  "actions_taken": [
    {{
      "issue_id": "ISSUE-001",
      "candidate_action": "merge|rename|retype|delete_orphan|set_name|mark_out_of_scope|normalize|preserve|skip|no_change",
      "details": "What was changed or why not",
      "result": "success|skipped|failed"
    }}
  ],
  "final_assessment": "What changed and what remains unresolved"
}}
```
"""
    return await _refine_with_prompt_async(prompt)


def refine_graph_with_context(review_raw: str, structured_issues: list, issue_ids: list) -> dict:
    """
    translated note(translated note,translated note)

    Args:
        review_raw: Reviewer Agent translated note
        structured_issues: translated note issues translated note
        issue_ids: translated note issue_id translated note
    """
    import asyncio

    if not structured_issues:
        return {
            "success": True,
            "message": "No issues to fix",
            "actions_taken": []
        }

    # translated note issues translated note prompt,translated note
    prompt = _build_contextual_refinement_prompt(review_raw, structured_issues, issue_ids)

    # translated note
    return asyncio.run(_refine_with_prompt_async(prompt))


def _build_contextual_refinement_prompt(review_raw: str, issues: list, issue_ids: list) -> str:
    """translated note prompt"""

    prompt = f"""You are the KG Refiner Agent.

You have received a review report identifying quality issues in the knowledge graph.
Your task is to fix the specific issues listed below.

## Original Review Report

{review_raw[:5000]}

## Structured Issues to Fix

"""

    for issue in issues:
        if issue.get("id") in issue_ids:
            prompt += f"""
### {issue.get('id', 'N/A')}
- Type: {issue.get('type', 'N/A')}
- Severity: {issue.get('severity', 'N/A')}
- Entity: {issue.get('entity', 'N/A')}
- Current: {issue.get('current_state', 'N/A')}
- Expected: {issue.get('expected_state', 'N/A')}
- Suggested Action: {issue.get('suggested_action', 'N/A')}
- PMIDs: {', '.join(issue.get('pmids_affected', []))}
"""

    prompt += """
## Your Task

For each issue above:
1. Use available tools to verify the issue (get_entity_info, Read original paper)
2. Execute the suggested action using modify_graph
3. Verify the fix was applied correctly
4. Document the action taken

## Available Tools

- `analyze_graph.py` - Get graph statistics
- `get_entity_info.py <entity> <type>` - Get entity details
- `detect_issues.py` - Detect remaining issues
- `modify_graph.py merge <a> <b> <target> [type]` - Merge entities
- `modify_graph.py rename <old> <new> <type>` - Rename entity
- `modify_graph.py retype <entity> <old_type> <new_type>` - Retype entity
- `modify_graph.py delete_orphan <entity> <type>` - Delete orphan entity only
- `modify_graph.py set_name <entity> <type> <display_name>` - Change display name only
- `modify_graph.py mark_out_of_scope <entity> <type> [reason]` - Flag connected out-of-scope entity
- `modify_graph.py delete <entity> <type>` - Delete disconnected entity
- `Read file_path: data/raw/{pmid}.json` - Read original paper

Start fixing the issues now.
"""

    return prompt
