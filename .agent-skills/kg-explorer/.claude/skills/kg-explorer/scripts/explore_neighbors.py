#!/usr/bin/env python3
"""
translated note Claims - translated note
translated note: python explore_neighbors.py <entity_name> <entity_type> [--direction both|subject|object]

translated note:
  python explore_neighbors.py yogurt food_product
  python explore_neighbors.py type_2_diabetes outcome --direction object
  python explore_neighbors.py Lactobacillus_rhamnosus strain

entity_type translated note: food_product, strain, outcome, population
"""

import json
import sys
import argparse
from typing import List, Dict, Any, Set, Tuple

from kg_utils import data_store, normalize_entity_name, find_claims_by_entity


def explore_neighbors(
    entity_name: str,
    entity_type: str,
    direction: str = "both"
) -> Dict[str, Any]:
    """
    translated note claims

    Args:
        entity_name: translated note (translated note "yogurt", "type_2_diabetes")
        entity_type: translated note (food, strain, outcome, population)
                     translated note V2 translated note "food_product" translated note "food"
        direction: translated note
            - "both": translated note subject translated note object translated note claims
            - "subject": translated note subject (translated note)
            - "object": translated note object (translated note)

    Returns:
        {
            "entity": entity_name,
            "entity_type": entity_type,
            "direction": direction,
            "total_claims": int,
            "as_subject": [...],  # direction != "object" translated note
            "as_object": [...],   # direction != "subject" translated note
            "related_entities": [...]  # translated note
        }
    """
    # V3: translated note NetworkX translated note
    G = data_store.get_kg_graph()

    # translated note V2 translated note entity_type translated note V3
    entity_type_v3 = entity_type
    if entity_type == "food_product":
        entity_type_v3 = "food"

    # translated note claims
    claims = find_claims_by_entity(G, entity_name, entity_type_v3, direction)
    as_subject_claims = claims.get("as_subject", [])
    as_object_claims = claims.get("as_object", [])

    # translated note
    related_entities: Set[Tuple[str, str]] = set()

    for claim in as_subject_claims:
        related_entities.add((
            claim.get("object_name", ""),
            claim.get("object_type", "")
        ))

    for claim in as_object_claims:
        related_entities.add((
            claim.get("subject_name", ""),
            claim.get("subject_type", "")
        ))

    # translated note claim translated note (V3 translated note)
    def format_claim(claim: Dict) -> Dict:
        result = {
            "claim_id": claim.get("claim_id"),
            "claim_text": claim.get("claim_text"),
            "subject": claim.get("subject_name"),
            "subject_type": claim.get("subject_type"),
            "object": claim.get("object_name"),
            "object_type": claim.get("object_type"),
            "direction": claim.get("direction"),
            "evidence_count": claim.get("evidence_count", 0),
            "confidence_score": claim.get("confidence_score", 0),
        }
        # V3: translated note evidence_list translated note evidence translated note
        evidence_list = claim.get("evidence_list", [])
        if evidence_list:
            first_ev = evidence_list[0]
            result["effect_size"] = first_ev.get("effect_size")
            result["p_value"] = first_ev.get("p_value")
            result["primary_pmid"] = first_ev.get("pmid")
        return result

    # translated note
    result = {
        "entity": entity_name,
        "entity_type": entity_type,
        "direction": direction,
        "total_claims": len(as_subject_claims) + len(as_object_claims),
        "related_entities_count": len(related_entities),
        "related_entities": sorted([
            {"name": name, "type": type_}
            for name, type_ in related_entities if name
        ], key=lambda x: x["name"])
    }

    if direction in ["both", "subject"]:
        result["as_subject"] = [format_claim(c) for c in as_subject_claims]
        result["as_subject_count"] = len(as_subject_claims)

    if direction in ["both", "object"]:
        result["as_object"] = [format_claim(c) for c in as_object_claims]
        result["as_object_count"] = len(as_object_claims)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Explore neighbors of an entity in the knowledge graph"
    )
    parser.add_argument("entity_name", help="Entity name (e.g., yogurt, type_2_diabetes)")
    parser.add_argument(
        "entity_type",
        choices=["food", "food_product", "strain", "outcome", "population"],
        help="Entity type (V3 uses: food, strain, outcome, population)"
    )
    parser.add_argument(
        "--direction",
        choices=["both", "subject", "object"],
        default="both",
        help="Traversal direction: 'subject'=this entity affects others, "
             "'object'=others affect this entity, 'both'=both directions"
    )
    args = parser.parse_args()

    try:
        result = explore_neighbors(args.entity_name, args.entity_type, args.direction)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except FileNotFoundError as e:
        print(json.dumps({
            "error": str(e),
            "entity": args.entity_name,
            "entity_type": args.entity_type
        }, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "error": f"Unexpected error: {str(e)}",
            "entity": args.entity_name,
            "entity_type": args.entity_type
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
