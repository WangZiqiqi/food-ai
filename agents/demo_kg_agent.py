#!/usr/bin/env python3
"""
KG-Agent translated note
translated note

translated note Agent translated note:
1. translated note claims
2. translated note claims translated note
3. translated note
4. translated note
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
KG_EXPLORER_DIR = PROJECT_ROOT / ".agent-skills" / "kg-explorer" / ".claude" / "skills" / "kg-explorer" / "scripts"


def run_tool(script: str, *args) -> Dict:
    """translated note JSON translated note"""
    script_path = KG_EXPLORER_DIR / script
    cmd = [sys.executable, str(script_path)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"Error running {script}: {result.stderr}")
        return {"error": result.stderr}
    return json.loads(result.stdout)


def agent_explore(question: str) -> Dict[str, Any]:
    """
    translated note Agent translated note

    translated note:
    1. translated note 3-5 translated note claims
    2. translated note claim translated note
    3. translated note
    4. translated note
    """
    print(f" translated note: {question}")
    print("=" * 70)

    # Step 1: translated note
    print("\n📍 Step 1: translated note claims")
    search_result = run_tool("vector_search.py", question, "--top_k", "5")

    if "error" in search_result:
        return {"error": f"translated note: {search_result['error']}"}

    claim_keys = [r["claim_id"] for r in search_result["results"]]
    print(f"   translated note {len(claim_keys)} translated note claims:")
    for i, r in enumerate(search_result["results"], 1):
        print(f"   {i}. [{r['similarity']:.3f}] {r['claim_id']}")

    # Step 2: translated note claims translated note
    print("\n📍 Step 2: translated note claims translated note")
    claims_details = []
    entities_to_explore = set()

    for claim_key in claim_keys:
        details = run_tool("get_claim_details.py", claim_key)
        if details.get("found"):
            claims_details.append(details)
            # translated note
            entities_to_explore.add((details["subject"]["name"], details["subject"]["type"]))
            entities_to_explore.add((details["object"]["name"], details["object"]["type"]))
            print(f"   ✓ {claim_key}: {details['subject']['name']} -> {details['object']['name']} ({details['direction']})")

    # Step 3: translated note
    print(f"\n📍 Step 3: translated note (translated note {len(entities_to_explore)} translated note)")

    # translated note
    food_entities = [(name, type_) for name, type_ in entities_to_explore if type_ in ["food", "food_product"]]
    outcome_entities = [(name, type_) for name, type_ in entities_to_explore if type_ == "outcome"]

    explored_claims = set(claim_keys)
    additional_claims = []

    # translated note 2 translated note
    for entity_name, entity_type in food_entities[:2]:
        print(f"\n   translated note {entity_name} ({entity_type})...")
        neighbors = run_tool("explore_neighbors.py", entity_name, entity_type, "--direction", "subject")

        if "as_subject" in neighbors:
            for claim in neighbors["as_subject"][:3]:  # translated note 3 translated note
                if claim["claim_id"] not in explored_claims:
                    explored_claims.add(claim["claim_id"])
                    additional_claims.append(claim)
                    print(f"     translated note claim: {claim['claim_id']} -> {claim['object']}")

    # translated note 2 translated note outcome
    for entity_name, entity_type in outcome_entities[:2]:
        print(f"\n   translated note {entity_name} ({entity_type})...")
        neighbors = run_tool("explore_neighbors.py", entity_name, entity_type, "--direction", "object")

        if "as_object" in neighbors:
            for claim in neighbors["as_object"][:3]:
                if claim["claim_id"] not in explored_claims:
                    explored_claims.add(claim["claim_id"])
                    additional_claims.append(claim)
                    print(f"     translated note claim: {claim['subject']} -> {claim['object']}")

    # Step 4: translated note
    print("\n📍 Step 4: translated note")

    all_claims = claims_details + additional_claims

    # translated note
    positive_count = sum(1 for c in all_claims if c.get("direction") == "positive")
    negative_count = sum(1 for c in all_claims if c.get("direction") == "negative")
    neutral_count = sum(1 for c in all_claims if c.get("direction") == "neutral")

    # translated note
    foods = set()
    outcomes = set()
    for c in all_claims:
        if isinstance(c, dict):
            # translated noteclaims_detailstranslated note(translated note)
            if "subject" in c and isinstance(c["subject"], dict):
                if c["subject"].get("type") in ["food", "food_product"]:
                    foods.add(c["subject"].get("name"))
                if c["object"].get("type") == "outcome":
                    outcomes.add(c["object"].get("name"))
            # translated noteadditional_claimstranslated note(translated note)
            else:
                if c.get("subject_type") in ["food", "food_product"] and c.get("subject"):
                    foods.add(c.get("subject"))
                if c.get("object_type") == "outcome" and c.get("object"):
                    outcomes.add(c.get("object"))

    # translated note
    evidence_refs = set()
    for c in claims_details:
        if "evidence_list" in c and c["evidence_list"]:
            for e in c["evidence_list"]:
                if e.get("pmid"):
                    evidence_refs.add(e["pmid"])

    answer = {
        "question": question,
        "answer": f"translated note {len(all_claims)} translated note,{', '.join(list(foods)[:3])} translated note {', '.join(list(outcomes)[:3])} translated note {positive_count} translated note.",
        "reasoning": f"translated note {len(claim_keys)} translated note claims,translated note {len(additional_claims)} translated note claims.",
        "statistics": {
            "total_claims": len(all_claims),
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
            "evidence_sources": list(evidence_refs)
        },
        "foods_involved": list(foods),
        "outcomes_involved": list(outcomes),
        "key_claims": [
            {
                "claim_id": c.get("claim_id"),
                "subject": c.get("subject", {}).get("name"),
                "object": c.get("object", {}).get("name"),
                "direction": c.get("direction"),
                "evidence_count": c.get("evidence_count"),
                "evidence_list": c.get("evidence_list", [])[:2]
            }
            for c in claims_details[:5]  # translated note 5 translated note
        ]
    }

    return answer


def main():
    """translated note"""
    test_questions = [
        "yogurt effect on diabetes",
        "kefir and cholesterol",
        "fermented food gut health"
    ]

    for question in test_questions:
        result = agent_explore(question)

        print("\n" + "=" * 70)
        print(" translated note")
        print("=" * 70)
        if "error" in result:
            print(f"\n translated note: {result['error']}")
            print("\n" + "-" * 70)
            continue

        print(f"\n💡 translated note: {result['answer']}")
        print(f"\n🧠 translated note: {result['reasoning']}")
        print(f"\n📈 translated note: {result['statistics']}")
        print(f"\n🍽️ translated note: {', '.join(result['foods_involved'])}")
        print(f"\n🎯 translated note: {', '.join(result['outcomes_involved'])}")

        print(f"\n📚 translated note ({len(result['key_claims'])} translated note):")
        for i, claim in enumerate(result['key_claims'], 1):
            print(f"   {i}. {claim['subject']} -> {claim['object']} ({claim['direction']})")
            if claim.get('evidence_list'):
                pmids = [e.get('pmid') for e in claim['evidence_list']]
                print(f"      translated note: PMID:{', '.join(pmids)}")
            print(f"      translated note: {claim.get('evidence_count', 0)}")

        print("\n" + "-" * 70)


if __name__ == "__main__":
    main()
