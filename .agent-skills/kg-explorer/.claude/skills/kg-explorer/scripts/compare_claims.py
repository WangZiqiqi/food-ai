#!/usr/bin/env python3
"""
Compare multiple claim nodes side by side.
"""

import argparse
import json

from kg_utils import data_store, get_claim_by_id


def compare_claims(claim_ids: list[str]) -> dict:
    graph = data_store.get_kg_graph()
    claims = []
    for claim_id in claim_ids:
        claim = get_claim_by_id(graph, claim_id)
        if claim:
            claims.append(
                {
                    "claim_id": claim_id,
                    "claim_text": claim.get("claim_text"),
                    "subject_name": claim.get("subject_name"),
                    "subject_type": claim.get("subject_type"),
                    "object_name": claim.get("object_name"),
                    "object_type": claim.get("object_type"),
                    "direction": claim.get("direction"),
                    "evidence_count": claim.get("evidence_count", 0),
                    "confidence_score": claim.get("confidence_score", 0.0),
                    "pmids": sorted({ev.get("pmid") for ev in claim.get("evidence_list", []) if ev.get("pmid")}),
                    "study_types": sorted({ev.get("study_type") for ev in claim.get("evidence_list", []) if ev.get("study_type")}),
                }
            )

    shared_subject = len({claim["subject_name"] for claim in claims}) == 1 if claims else False
    shared_object = len({claim["object_name"] for claim in claims}) == 1 if claims else False
    conflicting_direction = len({claim["direction"] for claim in claims if claim.get("direction")}) > 1

    return {
        "claim_ids": claim_ids,
        "found_claims": len(claims),
        "shared_subject": shared_subject,
        "shared_object": shared_object,
        "conflicting_direction": conflicting_direction,
        "claims": claims,
    }


def main():
    parser = argparse.ArgumentParser(description="Compare multiple claims")
    parser.add_argument("claim_ids", nargs="+")
    args = parser.parse_args()
    print(json.dumps(compare_claims(args.claim_ids), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
