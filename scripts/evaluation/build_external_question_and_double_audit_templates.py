#!/usr/bin/env python3
"""Create templates for external QA evaluation and two-reviewer claim audit."""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
from typing import Any


DEFAULT_EXTRACTION = Path("data/processed/final_graph/food_ai_graph.json")
DEFAULT_EXTERNAL_QA = Path("data/evaluation/external_food_science_questions_template_40.csv")
DEFAULT_DOUBLE_AUDIT = Path("data/evaluation/manual_claim_audit_double_reviewer_sample_30.csv")


SEED_QUESTIONS = [
    ("ext_001", "What evidence does the graph contain for kefir and gut microbiota outcomes?", "description"),
    ("ext_002", "What evidence does the graph contain for probiotics and LDL cholesterol?", "evidence_lookup"),
    ("ext_003", "Does the graph support a relationship between kombucha and adverse effects?", "evidence_lookup"),
    ("ext_004", "Compare kefir and yogurt for lipid-related outcomes.", "comparison"),
    ("ext_005", "Compare fermented dairy products and kombucha for gut-health outcomes.", "comparison"),
    ("ext_006", "What safety or adverse-event claims are indexed for probiotics?", "description"),
    ("ext_007", "Which fermented foods are linked to inflammation-related outcomes?", "description"),
    ("ext_008", "Does the graph contain direct evidence that kimchi improves dental enamel remineralization in children?", "no_answer_candidate"),
    ("ext_009", "What evidence is indexed for probiotic yogurt and glycemic outcomes?", "description"),
    ("ext_010", "What does the graph say about kefir and HbA1c?", "evidence_lookup"),
    ("ext_011", "Which claims connect fermented foods to gut microbiota composition?", "evidence_lookup"),
    ("ext_012", "Compare probiotics, kefir, and kombucha for gut microbiota outcomes.", "comparison"),
    ("ext_013", "What evidence is indexed for fermented dairy products and bone health?", "evidence_lookup"),
    ("ext_014", "Does the graph support miso effects on cancer-related outcomes?", "evidence_lookup"),
    ("ext_015", "What claims involve synbiotic supplements and gastrointestinal outcomes?", "description"),
    ("ext_016", "Which probiotic strains are linked to immune or inflammatory biomarkers?", "description"),
    ("ext_017", "Does the graph contain evidence for sauerkraut and blood pressure?", "no_answer_candidate"),
    ("ext_018", "What evidence is indexed for fermented milk and blood pressure?", "evidence_lookup"),
    ("ext_019", "Compare probiotic supplementation and fermented foods for immune outcomes.", "comparison"),
    ("ext_020", "What adverse-effect evidence is indexed for kombucha?", "evidence_lookup"),
    ("ext_021", "Which foods or interventions are linked to triglycerides?", "description"),
    ("ext_022", "What evidence is indexed for yogurt and cholesterol outcomes?", "description"),
    ("ext_023", "Does the graph contain direct evidence for natto and cognitive decline?", "no_answer_candidate"),
    ("ext_024", "What evidence is indexed for Lactobacillus rhamnosus GG and gut microbiota?", "evidence_lookup"),
    ("ext_025", "What evidence is indexed for Bifidobacterium longum and psychological or brain-related outcomes?", "description"),
    ("ext_026", "Compare evidence for probiotics and prebiotics on inflammatory markers.", "comparison"),
    ("ext_027", "What claims connect fermented foods to oxidative stress?", "evidence_lookup"),
    ("ext_028", "Does the graph support kombucha as an antimicrobial food system?", "evidence_lookup"),
    ("ext_029", "What graph evidence exists for fermented foods and type 2 diabetes risk?", "description"),
    ("ext_030", "Compare kefir and probiotic yogurt for glucose metabolism outcomes.", "comparison"),
    ("ext_031", "Which indexed claims have neutral or no-significant-effect findings for kefir?", "description"),
    ("ext_032", "What evidence is indexed for probiotics and constipation symptoms?", "evidence_lookup"),
    ("ext_033", "Does the graph contain direct evidence for tempeh and sleep quality?", "no_answer_candidate"),
    ("ext_034", "What safety claims are indexed for fermented foods as a broad category?", "description"),
    ("ext_035", "Which subjects are most connected to HDL cholesterol outcomes?", "description"),
    ("ext_036", "What evidence is indexed for plant sterol-enriched yogurt or milk and LDL cholesterol?", "evidence_lookup"),
    ("ext_037", "Compare fermented foods and probiotic supplements for inflammation outcomes.", "comparison"),
    ("ext_038", "Does the graph contain evidence for kimchi and oral-health outcomes?", "description"),
    ("ext_039", "What evidence is indexed for kefir and anticarcinogenic activity?", "evidence_lookup"),
    ("ext_040", "Which graph claims should be interpreted cautiously because direction is unclear?", "quality_review"),
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_external_qa(path: Path) -> None:
    fieldnames = [
        "question_id",
        "question",
        "question_type",
        "authored_by",
        "author_role",
        "expected_answer_notes",
        "expected_pmids_optional",
        "answer_usefulness",
        "pmid_traceability",
        "abstention_correct",
        "reviewer_notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for qid, question, question_type in SEED_QUESTIONS:
            writer.writerow(
                {
                    "question_id": qid,
                    "question": question,
                    "question_type": question_type,
                    "authored_by": "",
                    "author_role": "",
                    "expected_answer_notes": "",
                    "expected_pmids_optional": "",
                    "answer_usefulness": "",
                    "pmid_traceability": "",
                    "abstention_correct": "",
                    "reviewer_notes": "",
                }
            )


def primary_evidence(claim: dict[str, Any]) -> dict[str, Any]:
    evidence = claim.get("evidence_list") or []
    return evidence[0] if evidence else {}


def write_double_audit(path: Path, extraction: dict[str, Any], sample_size: int, seed: int) -> None:
    rng = random.Random(seed)
    claims = list(extraction.get("merged_claims", []))
    rng.shuffle(claims)
    selected = claims[:sample_size]
    fieldnames = [
        "audit_id",
        "claim_id",
        "claim_text",
        "subject_name",
        "subject_type",
        "object_name",
        "object_type",
        "direction",
        "effect_direction",
        "health_interpretation",
        "primary_pmid",
        "primary_evidence_snippet",
        "reviewer1_subject_correct",
        "reviewer1_outcome_correct",
        "reviewer1_direction_correct",
        "reviewer1_snippet_supports_claim",
        "reviewer1_pmid_traceable",
        "reviewer1_notes",
        "reviewer2_subject_correct",
        "reviewer2_outcome_correct",
        "reviewer2_direction_correct",
        "reviewer2_snippet_supports_claim",
        "reviewer2_pmid_traceable",
        "reviewer2_notes",
        "resolved_subject_correct",
        "resolved_outcome_correct",
        "resolved_direction_correct",
        "resolved_snippet_supports_claim",
        "resolved_pmid_traceable",
        "resolution_notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for idx, claim in enumerate(selected, start=1):
            evidence = primary_evidence(claim)
            writer.writerow(
                {
                    "audit_id": f"double_audit_{idx:03d}",
                    "claim_id": claim.get("claim_id"),
                    "claim_text": claim.get("claim_text"),
                    "subject_name": claim.get("subject_name"),
                    "subject_type": claim.get("subject_type"),
                    "object_name": claim.get("object_name"),
                    "object_type": claim.get("object_type"),
                    "direction": claim.get("direction"),
                    "effect_direction": claim.get("effect_direction", ""),
                    "health_interpretation": claim.get("health_interpretation", ""),
                    "primary_pmid": evidence.get("pmid", ""),
                    "primary_evidence_snippet": evidence.get("evidence_snippet", ""),
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction", type=Path, default=DEFAULT_EXTRACTION)
    parser.add_argument("--external-qa-output", type=Path, default=DEFAULT_EXTERNAL_QA)
    parser.add_argument("--double-audit-output", type=Path, default=DEFAULT_DOUBLE_AUDIT)
    parser.add_argument("--double-audit-size", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260528)
    args = parser.parse_args()

    extraction = load_json(args.extraction)
    write_external_qa(args.external_qa_output)
    write_double_audit(args.double_audit_output, extraction, args.double_audit_size, args.seed)
    print(f"wrote {args.external_qa_output}")
    print(f"wrote {args.double_audit_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
