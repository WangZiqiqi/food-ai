#!/usr/bin/env python3
"""
KG Refiner - translated note
translated noteclaimstranslated note
"""

import json
import pickle
import sys
import os
from pathlib import Path


DEFAULT_KG_PATH = os.getenv("FOOD_AI_REFINER_KG_PATH") or os.getenv("FOOD_AI_KG_PICKLE_PATH") or "data/processed/final_graph/food_ai_graph.pkl"


def get_entity_details(entity_name: str, entity_type: str, kg_path: str = DEFAULT_KG_PATH):
    """translated note"""
    with open(kg_path, 'rb') as f:
        G = pickle.load(f)

    # translated note
    entity_node_id = f"{entity_type}_{entity_name.lower().replace(' ', '_')}"

    if entity_node_id not in G.nodes:
        # translated note
        for node_id, data in G.nodes(data=True):
            if data.get('name', '').lower() == entity_name.lower():
                entity_node_id = node_id
                entity_type = data.get('node_type')
                break

    if entity_node_id not in G.nodes:
        print(json.dumps({"found": False, "entity": entity_name, "type": entity_type}, indent=2))
        return

    # translated noteclaims
    as_subject = []
    as_object = []

    for successor in G.successors(entity_node_id):
        node_data = G.nodes[successor]
        if node_data.get('node_type') == 'claim':
            as_subject.append({
                "claim_id": successor,
                "claim_text": node_data.get('claim_text'),
                "object": node_data.get('object_name'),
                "direction": node_data.get('direction'),
                "evidence_count": node_data.get('evidence_count', 0)
            })

    for predecessor in G.predecessors(entity_node_id):
        node_data = G.nodes[predecessor]
        if node_data.get('node_type') == 'claim':
            as_object.append({
                "claim_id": predecessor,
                "claim_text": node_data.get('claim_text'),
                "subject": node_data.get('subject_name'),
                "direction": node_data.get('direction'),
                "evidence_count": node_data.get('evidence_count', 0)
            })

    result = {
        "found": True,
        "entity": entity_name,
        "type": entity_type,
        "total_claims": len(as_subject) + len(as_object),
        "as_subject": as_subject,
        "as_object": as_object
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python get_entity_details.py <entity_name> <entity_type>", file=sys.stderr)
        sys.exit(1)

    get_entity_details(sys.argv[1], sys.argv[2])
