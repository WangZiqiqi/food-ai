#!/usr/bin/env python3
"""
translated note Claim translated note (V3 - Claim-Centric)
translated note: python get_claim_details.py <claim_id>
translated note: python get_claim_details.py 49766666c0b4

V3 translated note:
- translated note claim_id (12translated note) translated note claim_key
- Claim translated note evidence_list translated note
- translated note evidence translated note
"""

import json
import sys
import argparse
from typing import Optional, Dict, Any

from kg_utils import data_store, get_claim_by_id


def get_claim_details(claim_id: str) -> Optional[Dict[str, Any]]:
    """
    V3: translated note claim translated note (translated note evidence_list)

    Args:
        claim_id: V3 claim ID (translated note "49766666c0b4")

    Returns:
        Claim translated note,translated note evidence_list
    """
    G = data_store.get_kg_graph()

    claim = get_claim_by_id(G, claim_id)

    if claim is None:
        return {"found": False, "claim_id": claim_id}

    # V3: Claim translated note,translated note evidence_list
    result = {
        "found": True,
        "claim_id": claim.get("claim_id"),
        "claim_text": claim.get("claim_text"),
        "subject": {
            "name": claim.get("subject_name"),
            "type": claim.get("subject_type")
        },
        "object": {
            "name": claim.get("object_name"),
            "type": claim.get("object_type")
        },
        "direction": claim.get("direction"),
        "dose_info": claim.get("dose_info"),
        "evidence_count": claim.get("evidence_count", 0),
        "confidence_score": claim.get("confidence_score", 0.0),
        "evidence_list": claim.get("evidence_list", []),
        "merged_from": claim.get("merged_from", []),
        "first_seen": claim.get("first_seen"),
        "last_updated": claim.get("last_updated")
    }

    # translated note
    evidence_list = claim.get("evidence_list", [])
    if evidence_list:
        pmids = list(set([ev.get("pmid") for ev in evidence_list if ev.get("pmid")]))
        study_types = list(set([ev.get("study_type") for ev in evidence_list if ev.get("study_type")]))
        result["evidence_summary"] = {
            "total_evidence": len(evidence_list),
            "pmids": pmids,
            "study_types": study_types
        }

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Get V3 claim details with evidence_list"
    )
    parser.add_argument("claim_id", help="V3 Claim ID (e.g., 49766666c0b4)")
    args = parser.parse_args()

    try:
        result = get_claim_details(args.claim_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except FileNotFoundError as e:
        print(json.dumps({
            "error": str(e),
            "claim_id": args.claim_id
        }, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "error": f"Unexpected error: {str(e)}",
            "claim_id": args.claim_id
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
