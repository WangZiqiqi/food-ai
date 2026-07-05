#!/usr/bin/env python3
"""
Build manually curated Food-AI QA benchmark variants.

Outputs:
- a clean 120-item graph-positive benchmark with the manually rejected items
  replaced by clearer graph-backed questions;
- a 25-item no-answer / out-of-graph benchmark;
- a mixed benchmark combining both.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from generate_qa_benchmark_850 import corpus_by_pmid, make_item  # noqa: E402


EXTRACTION = PROJECT_ROOT / "data/processed/final_graph/food_ai_graph.json"
CORPUS = PROJECT_ROOT / "data/processed/selected_850_quality_llm_abstract_complete_2026-04-26.json"
SOURCE_120 = PROJECT_ROOT / "data/evaluation/query_benchmark_850_seed_120.json"
REVIEW_PASS_NEW = PROJECT_ROOT / "data/evaluation/query_benchmark_850_seed_120_new_review_pass.json"

CLEAN_120 = PROJECT_ROOT / "data/evaluation/query_benchmark_850_seed_120_clean.json"
NO_ANSWER_25 = PROJECT_ROOT / "data/evaluation/query_benchmark_850_no_answer_25.json"
MIXED_145 = PROJECT_ROOT / "data/evaluation/query_benchmark_850_clean_120_plus_no_answer_25.json"


REPLACEMENT_SPECS = [
    (
        "qa850_repl_001",
        "description",
        "What does the evidence say about the antimicrobial activity of kombucha?",
        ["7467b2d64d37"],
    ),
    (
        "qa850_repl_002",
        "description",
        "What does the evidence say about the antioxidant capacity of kombucha?",
        ["af359cbee272"],
    ),
    (
        "qa850_repl_003",
        "description",
        "What does the evidence say about kefir and Helicobacter pylori eradication?",
        ["e0cc0207281e"],
    ),
    (
        "qa850_repl_004",
        "description",
        "What does the evidence say about probiotic yogurt and LDL cholesterol?",
        ["1ab89c45e326"],
    ),
    (
        "qa850_repl_005",
        "evidence_lookup",
        "Which PubMed evidence supports the claim that kefir has antimicrobial activity?",
        ["7c60bc0048c5"],
    ),
    (
        "qa850_repl_006",
        "evidence_lookup",
        "Which PubMed evidence supports the claim that fermented foods have antioxidant capacity?",
        ["4e29460d11f3"],
    ),
    (
        "qa850_repl_007",
        "reason",
        "Why is kombucha relevant to gut microbiota according to the extracted literature evidence?",
        ["edec3f6e936d"],
    ),
    (
        "qa850_repl_008",
        "reason",
        "Why are probiotics relevant to immune function according to the extracted literature evidence?",
        ["eee3f64c516f"],
    ),
    (
        "qa850_repl_009",
        "reason",
        "Why is yogurt relevant to type 2 diabetes according to the extracted literature evidence?",
        ["0ddb73bbb56f"],
    ),
    (
        "qa850_repl_010",
        "reason",
        "Why is probiotic yogurt relevant to total cholesterol according to the extracted literature evidence?",
        ["e0b1fa517cca"],
    ),
    (
        "qa850_repl_011",
        "comparison",
        "Compare the evidence for fermented dairy products, kefir and kimchi with respect to immune function.",
        ["415a37dfddf4", "f4f782eaec4f", "57dfdf161a33"],
    ),
    (
        "qa850_repl_012",
        "comparison",
        "Compare the evidence for kefir, fermented foods and fermented milk products with respect to type 2 diabetes.",
        ["094ecb4e4a26", "dee63f484b57", "b45bc2720077"],
    ),
]


NO_ANSWER_QUESTIONS = [
    ("qa850_na_001", "Does fermented dragon fruit reduce migraine frequency in adults?"),
    ("qa850_na_002", "Is kombucha supported as a treatment for Parkinson's disease tremor severity?"),
    ("qa850_na_003", "Does kimchi improve dental enamel remineralization in children?"),
    ("qa850_na_004", "Which PubMed evidence shows that kefir prevents cataract progression?"),
    ("qa850_na_005", "Does probiotic yogurt improve hearing loss outcomes?"),
    ("qa850_na_006", "Is tempeh associated with reduced kidney stone recurrence?"),
    ("qa850_na_007", "Does sauerkraut improve endometriosis pain according to the graph?"),
    ("qa850_na_008", "Which evidence supports fermented oats as a therapy for glaucoma?"),
    ("qa850_na_009", "Does miso improve bone fracture healing time?"),
    ("qa850_na_010", "Is natto linked to lower risk of altitude sickness?"),
    ("qa850_na_011", "Does sourdough bread reduce symptoms of rheumatoid arthritis flare-ups?"),
    ("qa850_na_012", "Which PubMed evidence supports kefir for chronic tinnitus?"),
    ("qa850_na_013", "Does kombucha improve chemotherapy-induced hair loss?"),
    ("qa850_na_014", "Is fermented garlic supported for treating sleep apnea?"),
    ("qa850_na_015", "Does probiotic supplementation improve autism diagnostic scores in adults?"),
    ("qa850_na_016", "Which evidence shows that fermented soy milk treats psoriasis severity?"),
    ("qa850_na_017", "Does kimchi reduce asthma exacerbation frequency?"),
    ("qa850_na_018", "Is yogurt supported as a treatment for Alzheimer's disease progression?"),
    ("qa850_na_019", "Does kefir improve male infertility sperm motility in the graph?"),
    ("qa850_na_020", "Which evidence supports kombucha for lowering intraocular pressure?"),
    ("qa850_na_021", "Does fermented papaya prevent urinary tract infections?"),
    ("qa850_na_022", "Is probiotic cheese associated with improved thyroid hormone levels?"),
    ("qa850_na_023", "Does fermented black tea reduce epileptic seizure frequency?"),
    ("qa850_na_024", "Which PubMed evidence supports yogurt for treating acne scars?"),
    ("qa850_na_025", "Does fermented millet improve chronic back pain according to the graph?"),
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_no_answer_item(qid: str, question: str) -> dict[str, Any]:
    return {
        "id": qid,
        "question_type": "no_answer",
        "expected_answer_type": "no_answer",
        "question": question,
        "gold_claim_ids": [],
        "gold_pmids": [],
        "gold_subjects": [],
        "gold_outcomes": [],
        "gold_directions": [],
        "expected_answer": (
            "The graph is expected not to contain direct evidence for this question. "
            "A correct answer should abstain, say that no direct graph-backed evidence was found, "
            "and avoid citing unsupported claims as evidence."
        ),
        "retrieval_queries": [question],
        "source_evidence": {},
        "annotation_note": (
            "No-answer item manually authored to test abstention / out-of-graph behavior. "
            "Gold claim and PMID sets are intentionally empty."
        ),
    }


def main() -> None:
    extraction = load_json(EXTRACTION)
    corpus = load_json(CORPUS)
    source_120 = load_json(SOURCE_120)
    review_pass_new = load_json(REVIEW_PASS_NEW)
    claims_by_id = {claim["claim_id"]: claim for claim in extraction["merged_claims"]}
    pmid_to_article = corpus_by_pmid(corpus)

    replacement_items = []
    for qid, question_type, question, claim_ids in REPLACEMENT_SPECS:
        claims = [claims_by_id[claim_id] for claim_id in claim_ids]
        replacement_items.append(make_item(qid, question_type, question, claims, pmid_to_article))

    original_50 = source_120["items"][:50]
    clean_items = original_50 + review_pass_new["items"] + replacement_items
    if len(clean_items) != 120:
        raise RuntimeError(f"Expected 120 clean items, got {len(clean_items)}")
    if len({item["question"].lower().strip() for item in clean_items}) != len(clean_items):
        raise RuntimeError("Duplicate question text in clean benchmark")
    base_claim_ids = {
        claim_id
        for item in original_50 + review_pass_new["items"]
        for claim_id in item.get("gold_claim_ids", [])
    }
    replacement_claim_ids = [
        claim_id
        for item in replacement_items
        for claim_id in item.get("gold_claim_ids", [])
    ]
    if len(replacement_claim_ids) != len(set(replacement_claim_ids)):
        raise RuntimeError("Duplicate gold claim IDs among replacement items")
    overlap = sorted(base_claim_ids & set(replacement_claim_ids))
    if overlap:
        raise RuntimeError(f"Replacement items reuse existing gold claims: {overlap}")

    clean_payload = {
        "benchmark_id": "food_ai_qa_850_seed_v3_clean_120",
        "created_from": {
            "source_120": str(SOURCE_120.relative_to(PROJECT_ROOT)),
            "review_pass_new": str(REVIEW_PASS_NEW.relative_to(PROJECT_ROOT)),
            "extraction": str(EXTRACTION.relative_to(PROJECT_ROOT)),
            "corpus": str(CORPUS.relative_to(PROJECT_ROOT)),
        },
        "seed": source_120.get("seed"),
        "size": len(clean_items),
        "schema_version": 3,
        "description": (
            "Clean 120-question graph-positive QA benchmark. Original 50 questions are preserved; "
            "manually rejected appended items are replaced with clearer graph-backed questions."
        ),
        "replaced_rejected_count": 12,
        "replacement_item_ids": [item["id"] for item in replacement_items],
        "items": clean_items,
    }
    write_json(CLEAN_120, clean_payload)

    no_answer_items = [make_no_answer_item(qid, question) for qid, question in NO_ANSWER_QUESTIONS]
    no_answer_payload = {
        "benchmark_id": "food_ai_qa_850_no_answer_25",
        "created_from": {
            "clean_graph_positive_benchmark": str(CLEAN_120.relative_to(PROJECT_ROOT)),
        },
        "size": len(no_answer_items),
        "schema_version": 1,
        "description": (
            "Manual no-answer / out-of-graph QA benchmark for testing whether the Agent abstains "
            "when Food-AI has no direct graph-backed evidence."
        ),
        "items": no_answer_items,
    }
    write_json(NO_ANSWER_25, no_answer_payload)

    mixed_payload = {
        "benchmark_id": "food_ai_qa_850_clean_120_plus_no_answer_25",
        "created_from": {
            "clean_graph_positive_benchmark": str(CLEAN_120.relative_to(PROJECT_ROOT)),
            "no_answer_benchmark": str(NO_ANSWER_25.relative_to(PROJECT_ROOT)),
        },
        "size": len(clean_items) + len(no_answer_items),
        "schema_version": 1,
        "description": (
            "Mixed benchmark containing 120 clean graph-positive questions and 25 no-answer "
            "/ out-of-graph abstention questions."
        ),
        "items": clean_items + no_answer_items,
    }
    write_json(MIXED_145, mixed_payload)

    print(f"Wrote {len(clean_items)} clean graph-positive items to {CLEAN_120}")
    print(f"Wrote {len(no_answer_items)} no-answer items to {NO_ANSWER_25}")
    print(f"Wrote {len(mixed_payload['items'])} mixed items to {MIXED_145}")


if __name__ == "__main__":
    main()
