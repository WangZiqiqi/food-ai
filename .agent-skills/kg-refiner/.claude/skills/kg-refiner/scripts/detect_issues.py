#!/usr/bin/env python3
"""
KG Refiner - translated note
translated note, translated note, translated note
"""

import json
import pickle
import re
import os
from pathlib import Path
from collections import defaultdict


DEFAULT_KG_PATH = os.getenv("FOOD_AI_REFINER_KG_PATH") or os.getenv("FOOD_AI_KG_PICKLE_PATH") or "data/processed/final_graph/food_ai_graph.pkl"


def detect_issues(kg_path: str = DEFAULT_KG_PATH):
    """translated note"""
    with open(kg_path, 'rb') as f:
        G = pickle.load(f)

    issues = {
        "suspicious_entities": [],
        "duplicate_candidates": [],
        "potential_conflicts": [],
        "orphan_entities": []
    }

    # 1. translated note(translated notefoodtranslated note)
    food_blacklist_patterns = [
        r'^male_', r'^female_', r'^control_', r'^placebo$',
        r'^week', r'^day_', r'^month', r'^baseline$',
        r'^follow', r'^lab_diet$', r'^conditioning_'
    ]

    for node_id, data in G.nodes(data=True):
        if data.get('node_type') == 'food':
            name = data.get('name', '')
            for pattern in food_blacklist_patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    issues["suspicious_entities"].append({
                        "name": name,
                        "type": "food",
                        "issue": "translated note",
                        "pattern_matched": pattern
                    })
                    break

    # 2. translated note(translated note)
    foods = []
    for node_id, data in G.nodes(data=True):
        if data.get('node_type') == 'food':
            foods.append(data.get('name', ''))

    # translated note(translated note)
    for i, f1 in enumerate(foods):
        for f2 in foods[i+1:]:
            # translated note
            if f1 in f2 or f2 in f1:
                if abs(len(f1) - len(f2)) < max(len(f1), len(f2)) * 0.3:  # translated note
                    issues["duplicate_candidates"].append({
                        "entity_a": f1,
                        "entity_b": f2,
                        "reason": "translated note",
                        "suggested_merge": f1 if len(f1) < len(f2) else f2
                    })

    # 3. translated note(translated note)
    claim_pairs = defaultdict(list)
    for node_id, data in G.nodes(data=True):
        if data.get('node_type') == 'claim':
            pair_key = (data.get('subject_name'), data.get('object_name'))
            claim_pairs[pair_key].append({
                "claim_id": node_id,
                "direction": data.get('direction'),
                "evidence_count": data.get('evidence_count', 0)
            })

    for pair, claims in claim_pairs.items():
        directions = set(c['direction'] for c in claims if c['direction'])
        if len(directions) > 1:
            issues["potential_conflicts"].append({
                "subject": pair[0],
                "object": pair[1],
                "conflicting_directions": list(directions),
                "claims": claims
            })

    # translated note
    issues["summary"] = {
        "suspicious_entities_count": len(issues["suspicious_entities"]),
        "duplicate_candidates_count": len(issues["duplicate_candidates"]),
        "potential_conflicts_count": len(issues["potential_conflicts"])
    }

    print(json.dumps(issues, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    detect_issues()
