#!/usr/bin/env python3
"""
Search entity nodes by name/alias and return lightweight graph context.
"""

import argparse
import json
from typing import Any

from kg_utils import data_store


def _score(query: str, candidate: str) -> float:
    q = query.lower().strip()
    c = candidate.lower().strip()
    if q == c:
        return 1.0
    if q in c or c in q:
        return 0.9
    q_tokens = set(q.replace("_", " ").split())
    c_tokens = set(c.replace("_", " ").split())
    if not q_tokens or not c_tokens:
        return 0.0
    overlap = len(q_tokens & c_tokens) / len(q_tokens | c_tokens)
    return overlap


def search_entities(query: str, entity_type: str | None = None, top_k: int = 10) -> dict[str, Any]:
    graph = data_store.get_kg_graph()
    results = []

    for node_id, data in graph.nodes(data=True):
        node_type = data.get("node_type")
        if node_type not in {"food", "strain", "outcome", "population", "intervention", "intervention_category", "bioactive_compound", "biological_factor", "microbial_metabolite", "microbial_ecosystem"}:
            continue
        if entity_type and node_type != entity_type:
            continue

        name = data.get("name", "")
        score = _score(query, name)
        if score <= 0:
            continue

        claim_count = len(list(graph.successors(node_id))) + len(list(graph.predecessors(node_id)))
        results.append(
            {
                "node_id": node_id,
                "name": name,
                "entity_type": node_type,
                "score": round(score, 4),
                "claim_count": claim_count,
            }
        )

    results.sort(key=lambda item: (item["score"], item["claim_count"]), reverse=True)
    return {
        "query": query,
        "entity_type_filter": entity_type,
        "top_k": top_k,
        "results": results[:top_k],
    }


def main():
    parser = argparse.ArgumentParser(description="Search entity nodes by name")
    parser.add_argument("query")
    parser.add_argument("--entity-type", default=None)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(search_entities(args.query, args.entity_type, args.top_k), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
