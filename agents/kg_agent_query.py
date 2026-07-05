#!/usr/bin/env python3
"""
KG-Agent query entry point.
Uses the Claude Agent SDK to autonomously explore the knowledge graph.

Usage:
    python kg_agent_query.py "yogurt effect on diabetes"
    python kg_agent_query.py "which probiotic is best for cholesterol reduction"
"""

import os
import sys

import json
import argparse
import asyncio
from pathlib import Path
from sdk_runtime import (
    configure_sdk_environment,
    create_debug_options,
    extract_text_and_tool_calls,
    log_stream_event,
)

# translated note
PROJECT_ROOT = Path(__file__).parent.parent.resolve()  # translated note agents/ translated note
try:
    configure_sdk_environment(PROJECT_ROOT)
except RuntimeError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    sys.exit(1)

PYTHON_BIN = sys.executable


async def query_with_agent_async(question: str, max_iterations: int = 15) -> dict:
    """
    translated note Claude Agent SDK translated note(translated note)
    """
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError as e:
        print(f"translated note: translated note claude-agent-sdk: {e}")
        sys.exit(1)

    tool_profile = os.environ.get("FOOD_AI_AGENT_TOOL_PROFILE", "full").strip().lower()
    if tool_profile == "claim_only":
        tools_block = f"""### 1. Semantic Vector Search
```
{PYTHON_BIN} .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/vector_search.py "<query>" --top_k 5
```
Returns ranked claim_ids by semantic similarity. Use natural-language queries in English.

### 2. Claim Details
```
{PYTHON_BIN} .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/get_claim_details.py <claim_id>
```
Returns the full claim including:
- `evidence_list`: all supporting evidence (PMID, study_type, effect_size, p_value, CI)
- `evidence_count`, `confidence_score`

Do not use entity search, neighbor exploration, PMID search, or claim comparison tools in this run.
This is a claim-only ablation profile."""
        strategy_block = """1. **Recall**: use `vector_search.py` to retrieve 5–10 relevant claims.
2. **Assess**: use `get_claim_details.py` on the strongest candidate claims; check subject, outcome, direction, PMIDs, evidence_count, and evidence snippets.
3. **Abstain if needed**: if retrieved claims are only adjacent and do not directly support the question, say that no direct graph-backed evidence was found.
4. **Synthesise**: produce a structured answer with PMID citations and note uncertainty."""
    else:
        tools_block = f"""### 1. Semantic Vector Search
```
{PYTHON_BIN} .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/vector_search.py "<query>" --top_k 5
```
Returns ranked claim_ids by semantic similarity. Use natural-language queries in English.

### 2. Claim Details
```
{PYTHON_BIN} .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/get_claim_details.py <claim_id>
```
Returns the full claim including:
- `evidence_list`: all supporting evidence (PMID, study_type, effect_size, p_value, CI)
- `evidence_count`, `confidence_score`

### 3. Entity Neighbor Exploration
```
{PYTHON_BIN} .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/explore_neighbors.py <entity_name> <entity_type> [--direction subject|object|both]
```
entity_type options: food_product, strain, outcome, population

### 4. Entity Search
```
{PYTHON_BIN} .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/search_entities.py "<query>" --top-k 10
```
Use this when the user asks about a food, strain, outcome, or concept and you need to find the best matching node names first.

### 5. PMID Trace
```
{PYTHON_BIN} .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/search_by_pmid.py <pmid>
```
Use this when a paper is central to the question or when you need to verify what claims a specific PMID contributes.

### 6. Claim Compare
```
{PYTHON_BIN} .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/compare_claims.py <claim_id_1> <claim_id_2> [<claim_id_3> ...]
```
Use this to compare multiple candidate claims side by side and identify conflicts or shared subject/object pairs."""
        strategy_block = """1. **Anchor the query**: if the question mentions a concrete concept, first use `search_entities.py` to identify the right graph node names.
2. **Recall**: use `vector_search.py` to retrieve 5–10 relevant claims.
3. **Assess**: use `get_claim_details.py` on the strongest candidate claims; check study_type, PMIDs, evidence_count, and effect_size.
4. **Trace source papers**: if a PMID becomes important, use `search_by_pmid.py` to inspect the paper's graph footprint.
5. **Expand**: use `explore_neighbors.py` to gather nearby evidence and related outcomes/interventions.
6. **Compare**: if multiple claims look similar or conflicting, use `compare_claims.py` before concluding.
7. **Synthesise**: produce a structured answer with PMID citations and note any uncertainty."""

    prompt = f"""You are a Food-AI knowledge graph research assistant (V3 - Claim-Centric architecture).
Use the available tools to explore the knowledge graph and answer the user's question with
evidence-based reasoning.

## Core Concepts
- **Claim** is the central node, containing an `evidence_list` (one or more literature sources).
- Prefer claims with higher `evidence_count` (more evidence support).
- `direction`: "positive" = beneficial, "negative" = harmful/inhibitory, "neutral" = no significant effect.

## User Question
"{question}"

## Available Tools (invoked via the Bash tool)

{tools_block}

## Exploration Strategy

{strategy_block}

### Evidence Quality Tiers
- **High**: evidence_count ≥ 3, RCT or Meta-analysis, confidence_score ≥ 0.8
- **Moderate**: evidence_count 1–2, RCT present, confidence_score 0.5–0.8
- **Low**: evidence_count = 1, review/unknown only, confidence_score < 0.5

## Required Output (strict JSON)
```json
{{
  "answer": "Full answer in English, citing PMIDs inline.",
  "reasoning": "Step-by-step description of the tools used and exploration path.",
  "confidence": "high | medium | low",
  "foods_found": ["yogurt", "kefir"],
  "outcomes_found": ["blood_glucose", "cholesterol"],
  "claims_referenced": ["claim_id_1", "claim_id_2"],
  "evidence_summary": [
    {{"pmid": "40591489", "study_type": "RCT", "effect_size": "-0.5%", "p_value": "<0.01"}}
  ],
  "conflicts_noted": ["claim_xyz conflicts with claim_abc (opposing directions)"]
}}
```

Begin exploration now. Make autonomous decisions about the exploration path and return your answer as JSON."""

    print(f" translated note Agent SDK...")
    print(f"   translated note: {PROJECT_ROOT}")

    try:
        debug_enabled = os.environ.get("FOOD_AI_AGENT_DEBUG", "").lower() in {
            "1",
            "true",
            "yes",
        }
        debug_options, debug_state = create_debug_options(debug_enabled)

        # translated note - translated note skill,translated note kg-explorer
        settings_path = os.environ.get("FOOD_AI_AGENT_SETTINGS")
        model_name = os.environ.get("FOOD_AI_AGENT_MODEL") or os.environ.get("ANTHROPIC_MODEL")
        options = ClaudeAgentOptions(
            cwd=str(PROJECT_ROOT),
            permission_mode='bypassPermissions',  # translated note:translated note,translated note Agent translated note
            add_dirs=[str(PROJECT_ROOT / ".agent-skills" / "kg-explorer")],  # translated note skill
            max_turns=max_iterations,
            settings=str(Path(settings_path).expanduser()) if settings_path else None,
            model=model_name,
            **debug_options,
        )

        # SDK translated note
        response_stream = query(
            prompt=prompt,
            options=options
        )

        # translated note
        full_response = []
        tool_calls = []
        iterations = 0

        async for event in response_stream:
            event_type = type(event).__name__
            if getattr(event, "session_id", None) and not debug_state.get("session_id"):
                debug_state["session_id"] = getattr(event, "session_id")
            texts, event_tool_calls = extract_text_and_tool_calls(event)
            if debug_enabled:
                log_stream_event(event, texts, event_tool_calls, debug_state)
            full_response.extend(texts)
            tool_calls.extend(event_tool_calls)
            if event_type == 'ResultMessage':
                iterations += 1

        return {
            "question": question,
            "agent_response": "".join(full_response),
            "tool_calls": tool_calls,
            "iterations": iterations,
            "session_id": debug_state.get("session_id"),
            "transcript_paths": debug_state.get("transcript_paths", []),
            "success": True
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "question": question,
            "error": str(e),
            "success": False
        }


def query_with_agent(question: str, max_iterations: int = 15) -> dict:
    """Synchronous wrapper around query_with_agent_async."""
    return asyncio.run(query_with_agent_async(question, max_iterations))


def main():
    parser = argparse.ArgumentParser(
        description="KG-Agent Query — autonomously explore the knowledge graph"
    )
    parser.add_argument("question", help="Research question in natural language (English)")
    parser.add_argument("--max-iterations", type=int, default=15,
                        help="Maximum agent iterations (default: 15)")
    args = parser.parse_args()

    print("=" * 70)
    print(f"Question: {args.question}")
    print("Starting Agent exploration...")
    print("=" * 70)

    result = query_with_agent(args.question, args.max_iterations)

    if not result.get("success"):
        print(f"\nERROR: {result.get('error')}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("Agent exploration complete")
    print("=" * 70)
    if result.get("session_id"):
        print(f"Session ID: {result['session_id']}")
    if result.get("transcript_paths"):
        print("Transcript paths:")
        for path in result["transcript_paths"]:
            print(f"  - {path}")

    response_text = result.get("agent_response", "")

    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)

    if json_match:
        try:
            answer_data = json.loads(json_match.group(1))
            print(f"\nAnswer:\n{answer_data.get('answer', 'N/A')}")
            print(f"\nReasoning:\n{answer_data.get('reasoning', 'N/A')}")

            if answer_data.get('foods_found'):
                print(f"\nFoods: {', '.join(answer_data['foods_found'])}")
            if answer_data.get('outcomes_found'):
                print(f"Outcomes: {', '.join(answer_data['outcomes_found'])}")

            print(f"\nConfidence: {answer_data.get('confidence', 'N/A')}")

            evidence_list = answer_data.get('evidence_summary', [])
            print(f"\nEvidence summary ({len(evidence_list)} entries):")
            for i, ev in enumerate(evidence_list[:5], 1):
                pmid = ev.get('pmid', 'N/A')
                stype = ev.get('study_type', 'N/A')
                ef = ev.get('effect_size') or 'N/A'
                pv = ev.get('p_value') or 'N/A'
                print(f"  {i}. PMID:{pmid} | {stype} | effect: {ef} | p: {pv}")
                if ev.get('snippet'):
                    snippet = ev['snippet'][:100] + "..." if len(ev['snippet']) > 100 else ev['snippet']
                    print(f"     Snippet: {snippet}")

            if answer_data.get('conflicts_noted'):
                print(f"\nConflicts noted:")
                for c in answer_data['conflicts_noted']:
                    print(f"  - {c}")

        except json.JSONDecodeError as e:
            print(f"\nWARNING: Could not parse JSON output: {e}")
            print("\nRaw output:")
            print(response_text[-2000:] if len(response_text) > 2000 else response_text)
    else:
        print("\nAgent raw output:")
        print("-" * 70)
        print(response_text[-3000:] if len(response_text) > 3000 else response_text)
        print("-" * 70)

    print(f"\nStats: iterations={result.get('iterations', 'N/A')}, "
          f"tool_calls={len(result.get('tool_calls', []))}")

    # Save full result
    output_file = Path("data/agent_query_result.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Full result saved to: {output_file}")


if __name__ == "__main__":
    main()
