#!/usr/bin/env python3
"""
KG Refiner - translated note
translated note, translated note, translated note
"""

import json
import pickle
import sys
import os
from pathlib import Path
from collections import Counter, defaultdict


DEFAULT_KG_PATH = os.getenv("FOOD_AI_REFINER_KG_PATH") or os.getenv("FOOD_AI_KG_PICKLE_PATH") or "data/processed/final_graph/food_ai_graph.pkl"


def get_graph_stats(kg_path: str = DEFAULT_KG_PATH):
    """translated note"""
    with open(kg_path, 'rb') as f:
        G = pickle.load(f)

    # translated note
    node_types = Counter()
    for node_id, data in G.nodes(data=True):
        node_types[data.get('node_type', 'unknown')] += 1

    # translated note
    edge_count = G.number_of_edges()

    # Claimtranslated note
    claims = []
    for node_id, data in G.nodes(data=True):
        if data.get('node_type') == 'claim':
            claims.append({
                'claim_id': node_id,
                'subject': data.get('subject_name'),
                'object': data.get('object_name'),
                'direction': data.get('direction'),
                'evidence_count': data.get('evidence_count', 0)
            })

    # translated note
    foods = []
    strains = []
    outcomes = []

    for node_id, data in G.nodes(data=True):
        nt = data.get('node_type')
        name = data.get('name', '')
        if nt == 'food':
            foods.append(name)
        elif nt == 'strain':
            strains.append(name)
        elif nt == 'outcome':
            outcomes.append(name)

    # translated noteclaimstranslated note
    entity_claims = defaultdict(int)
    for node_id, data in G.nodes(data=True):
        if data.get('node_type') == 'claim':
            entity_claims[data.get('subject_name')] += 1
            entity_claims[data.get('object_name')] += 1

    result = {
        "node_stats": dict(node_types),
        "total_nodes": G.number_of_nodes(),
        "total_edges": edge_count,
        "total_claims": len(claims),
        "foods": sorted(foods),
        "strains": sorted(strains),
        "outcomes_sorted_by_claims": sorted(entity_claims.items(), key=lambda x: x[1], reverse=True)[:30],
        "foods_top": sorted([(f, entity_claims[f]) for f in foods], key=lambda x: x[1], reverse=True)[:15],
        "strains_top": sorted([(s, entity_claims[s]) for s in strains], key=lambda x: x[1], reverse=True)[:10]
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    get_graph_stats()
