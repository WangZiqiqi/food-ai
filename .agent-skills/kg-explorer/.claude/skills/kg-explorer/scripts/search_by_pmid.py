#!/usr/bin/env python3
"""
Trace all claim nodes that cite a given PMID.
"""

import argparse
import json
from typing import Any

from kg_utils import data_store


def search_by_pmid(pmid: str) -> dict[str, Any]:
    graph = data_store.get_kg_graph()
    claims = []
    for node_id, data in graph.nodes(data=True):
        if data.get("node_type") != "claim":
            continue
        for evidence in data.get("evidence_list", []):
            if evidence.get("pmid") == pmid:
                claims.append(
                    {
                        "claim_id": node_id,
                        "claim_text": data.get("claim_text"),
                        "subject_name": data.get("subject_name"),
                        "subject_type": data.get("subject_type"),
                        "object_name": data.get("object_name"),
                        "object_type": data.get("object_type"),
                        "direction": data.get("direction"),
                        "study_type": evidence.get("study_type"),
                        "effect_size": evidence.get("effect_size"),
                        "p_value": evidence.get("p_value"),
                    }
                )
                break

    return {
        "pmid": pmid,
        "claim_count": len(claims),
        "claims": claims,
    }


def main():
    parser = argparse.ArgumentParser(description="Find graph claims supported by a PMID")
    parser.add_argument("pmid")
    args = parser.parse_args()
    print(json.dumps(search_by_pmid(args.pmid), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
