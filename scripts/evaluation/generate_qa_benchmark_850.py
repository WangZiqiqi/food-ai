#!/usr/bin/env python3
"""
Generate a fixed QA benchmark from the 850-paper Food-AI graph.

The benchmark is intentionally gold-labeled from existing graph claims and
their source evidence snippets so retrieval evaluation can be reproduced.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_EXTRACTION = Path("data/processed/final_graph/food_ai_graph.json")
DEFAULT_CORPUS = Path("data/processed/selected_850_quality_llm_abstract_complete_2026-04-26.json")
DEFAULT_OUTPUT = Path("data/evaluation/query_benchmark_850_seed.json")

TARGET_TYPE_RATIOS = {
    "description": 0.34,
    "evidence_lookup": 0.21,
    "reason": 0.21,
    "comparison": 0.24,
}

QUESTIONABLE_SUBJECT_TERMS = {
    "age",
    "aging",
    "bile_acid_metabolism_modulation",
    "constipation_prevention",
    "dna_sequencing_technologies",
    "equol",
    "escitalopram",
    "gut_microbiota",
    "bile_acid_metabolism",
    "microbiota",
    "science-driven_fermentation",
    "sustainable_feedstocks",
}

QUESTIONABLE_SUBJECT_PATTERNS = (
    "sequencing",
    "prevention",
    "metabolism_modulation",
    "metabolites",
    "technologies",
)


def humanize(value: str) -> str:
    return value.replace("_", " ").strip()


def direction_phrase(direction: str) -> str:
    return {
        "positive": "a positive reported effect or association",
        "negative": "a negative reported effect or association",
        "neutral": "no statistically significant or neutral reported effect",
    }.get(direction, f"a {direction} reported effect")


def normalize_question(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def corpus_by_pmid(corpus: list[dict[str, Any]] | dict[str, Any]) -> dict[str, dict[str, Any]]:
    if isinstance(corpus, dict):
        corpus = corpus.get("articles", [])
    result = {}
    for item in corpus:
        pmid = str(item.get("pmid", "")).strip()
        if pmid:
            result[pmid] = item
    return result


def source_records(claim: dict[str, Any], pmid_to_article: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for evidence in claim.get("evidence_list", []):
        pmid = str(evidence.get("pmid", "")).strip()
        article = pmid_to_article.get(pmid, {})
        records.append(
            {
                "pmid": pmid,
                "title": article.get("title") or "",
                "study_type": evidence.get("study_type"),
                "effect_size": evidence.get("effect_size"),
                "p_value": evidence.get("p_value"),
                "confidence_interval": evidence.get("confidence_interval"),
                "evidence_snippet": evidence.get("evidence_snippet") or "",
                "abstract_excerpt": (article.get("abstract") or "")[:900],
            }
        )
    return records


def expected_answer_for_claim(claim: dict[str, Any], sources: list[dict[str, Any]]) -> str:
    subject = humanize(claim["subject_name"])
    outcome = humanize(claim["object_name"])
    pmids = ", ".join(sorted({s["pmid"] for s in sources if s["pmid"]}))
    snippet = next((s["evidence_snippet"] for s in sources if s["evidence_snippet"]), "")
    answer = (
        f"The graph supports that {subject} has {direction_phrase(claim['direction'])} "
        f"on {outcome}. Gold evidence PMID(s): {pmids}."
    )
    if snippet:
        answer += f" Key source evidence: {snippet}"
    return answer


def make_item(
    qid: str,
    question_type: str,
    question: str,
    claims: list[dict[str, Any]],
    pmid_to_article: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    sources_by_claim = {
        claim["claim_id"]: source_records(claim, pmid_to_article) for claim in claims
    }
    gold_pmids = sorted(
        {
            source["pmid"]
            for sources in sources_by_claim.values()
            for source in sources
            if source["pmid"]
        }
    )
    if len(claims) == 1:
        expected_answer = expected_answer_for_claim(claims[0], sources_by_claim[claims[0]["claim_id"]])
    else:
        parts = []
        for claim in claims:
            parts.append(
                f"{humanize(claim['subject_name'])}: {claim['direction']} effect on "
                f"{humanize(claim['object_name'])}"
            )
        expected_answer = (
            "The answer should recover these gold claim directions: "
            + "; ".join(parts)
            + f". Gold PMIDs: {', '.join(gold_pmids)}."
        )

    retrieval_queries = [question]
    for claim in claims:
        retrieval_queries.append(
            f"{humanize(claim['subject_name'])} effect on {humanize(claim['object_name'])}"
        )
        retrieval_queries.append(
            f"{humanize(claim['subject_name'])} {claim['direction']} {humanize(claim['object_name'])}"
        )

    return {
        "id": qid,
        "question_type": question_type,
        "question": question,
        "gold_claim_ids": [claim["claim_id"] for claim in claims],
        "gold_pmids": gold_pmids,
        "gold_subjects": sorted({claim["subject_name"] for claim in claims}),
        "gold_outcomes": sorted({claim["object_name"] for claim in claims}),
        "gold_directions": sorted({claim["direction"] for claim in claims}),
        "expected_answer": expected_answer,
        "retrieval_queries": list(dict.fromkeys(retrieval_queries)),
        "source_evidence": sources_by_claim,
        "annotation_note": (
            "Gold labels were created from extraction_850 merged claims and checked "
            "against the stored source evidence snippets / abstract metadata."
        ),
    }


def eligible_claims(extraction: dict[str, Any]) -> list[dict[str, Any]]:
    claims = []
    for claim in extraction["merged_claims"]:
        if claim.get("subject_type") not in {"food", "strain"}:
            continue
        if claim.get("object_type") != "outcome":
            continue
        if not claim.get("claim_id") or not claim.get("subject_name") or not claim.get("object_name"):
            continue
        if not claim.get("evidence_list"):
            continue
        if not any(ev.get("evidence_snippet") for ev in claim["evidence_list"]):
            continue
        subject_lower = claim["subject_name"].lower()
        if subject_lower in QUESTIONABLE_SUBJECT_TERMS:
            continue
        if any(pattern in subject_lower for pattern in QUESTIONABLE_SUBJECT_PATTERNS):
            continue
        claims.append(claim)
    return claims


def diversified_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        claims,
        key=lambda c: (
            -int(c.get("evidence_count") or 0),
            -float(c.get("confidence_score") or 0),
            c.get("subject_name", ""),
            c.get("object_name", ""),
        ),
    )
    selected = []
    seen_subjects = set()
    seen_pairs = set()
    for claim in ranked:
        pair = (claim["subject_name"], claim["object_name"])
        if pair in seen_pairs:
            continue
        if claim["subject_name"] in seen_subjects and len(selected) < 35:
            continue
        selected.append(claim)
        seen_subjects.add(claim["subject_name"])
        seen_pairs.add(pair)
    return selected + [claim for claim in ranked if claim not in selected]


def build_benchmark(
    extraction: dict[str, Any],
    corpus: list[dict[str, Any]],
    size: int,
    seed: int,
    extraction_path: Path = DEFAULT_EXTRACTION,
    corpus_path: Path = DEFAULT_CORPUS,
) -> dict[str, Any]:
    rng = random.Random(seed)
    pmid_to_article = corpus_by_pmid(corpus)
    claims = diversified_claims(eligible_claims(extraction))

    items: list[dict[str, Any]] = []
    used_claim_ids = set()

    def take_claim() -> dict[str, Any]:
        for claim in claims:
            if claim["claim_id"] not in used_claim_ids:
                used_claim_ids.add(claim["claim_id"])
                return claim
        raise RuntimeError("not enough eligible claims")

    target_counts = target_type_counts(size)
    single_specs = [
        ("description", target_counts["description"]),
        ("evidence_lookup", target_counts["evidence_lookup"]),
        ("reason", target_counts["reason"]),
    ]
    qnum = 1
    for question_type, count in single_specs:
        for _ in range(count):
            claim = take_claim()
            subject = humanize(claim["subject_name"])
            outcome = humanize(claim["object_name"])
            if question_type == "description":
                question = f"What does the evidence say about the effect of {subject} on {outcome}?"
            elif question_type == "evidence_lookup":
                question = (
                    f"Which PubMed evidence supports the claim that {subject} affects {outcome}, "
                    "and what direction is reported?"
                )
            else:
                question = (
                    f"Why is {subject} relevant to {outcome} according to the extracted literature evidence?"
                )
            items.append(make_item(f"qa850_{qnum:03d}", question_type, question, [claim], pmid_to_article))
            qnum += 1

    by_outcome: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        by_outcome[claim["object_name"]].append(claim)

    comparison_groups = []
    for outcome, group in by_outcome.items():
        unique_subjects = {}
        for claim in sorted(
            group,
            key=lambda c: (-int(c.get("evidence_count") or 0), -float(c.get("confidence_score") or 0)),
        ):
            unique_subjects.setdefault(claim["subject_name"], claim)
        if len(unique_subjects) >= 2:
            comparison_groups.append((outcome, list(unique_subjects.values())[:3]))
    rng.shuffle(comparison_groups)

    comparison_count = min(target_counts["comparison"], max(0, size - len(items)))
    for outcome, group in comparison_groups[:comparison_count]:
        subjects = [humanize(claim["subject_name"]) for claim in group]
        question = (
            f"Compare the evidence for {', '.join(subjects[:-1])} and {subjects[-1]} "
            f"with respect to {humanize(outcome)}."
        )
        items.append(make_item(f"qa850_{qnum:03d}", "comparison", question, group, pmid_to_article))
        qnum += 1

    return {
        "benchmark_id": "food_ai_qa_850_seed_v1",
        "created_from": {
            "extraction": str(extraction_path),
            "corpus": str(corpus_path),
        },
        "seed": seed,
        "size": len(items),
        "schema_version": 1,
        "description": (
            "Fixed QA benchmark for measuring Food-AI 850-graph retrieval and agent recall. "
            "Gold labels contain claim IDs and PMIDs derived from source-backed graph claims."
        ),
        "items": items[:size],
    }


def target_type_counts(size: int) -> dict[str, int]:
    counts = {
        qtype: int(round(size * ratio))
        for qtype, ratio in TARGET_TYPE_RATIOS.items()
    }
    diff = size - sum(counts.values())
    counts["comparison"] += diff
    return counts


def build_extended_benchmark(
    extraction: dict[str, Any],
    corpus: list[dict[str, Any]],
    size: int,
    seed: int,
    existing: dict[str, Any],
    extraction_path: Path = DEFAULT_EXTRACTION,
    corpus_path: Path = DEFAULT_CORPUS,
) -> dict[str, Any]:
    rng = random.Random(seed)
    pmid_to_article = corpus_by_pmid(corpus)
    claims = diversified_claims(eligible_claims(extraction))
    existing_items = list(existing.get("items", []))
    items = existing_items[:size]
    used_claim_ids = {
        claim_id
        for item in items
        for claim_id in item.get("gold_claim_ids", [])
    }
    used_questions = {normalize_question(item["question"]) for item in items}
    qnum = len(items) + 1

    existing_counts = Counter(item["question_type"] for item in items)
    target_counts = target_type_counts(size)

    def unused_single_claim() -> dict[str, Any] | None:
        for claim in claims:
            if claim["claim_id"] not in used_claim_ids:
                return claim
        return None

    def add_single(question_type: str) -> bool:
        nonlocal qnum
        claim = unused_single_claim()
        while claim is not None:
            subject = humanize(claim["subject_name"])
            outcome = humanize(claim["object_name"])
            if question_type == "description":
                question = f"What does the evidence say about the effect of {subject} on {outcome}?"
            elif question_type == "evidence_lookup":
                question = (
                    f"Which PubMed evidence supports the claim that {subject} affects {outcome}, "
                    "and what direction is reported?"
                )
            else:
                question = (
                    f"Why is {subject} relevant to {outcome} according to the extracted literature evidence?"
                )
            used_claim_ids.add(claim["claim_id"])
            if normalize_question(question) not in used_questions:
                items.append(make_item(f"qa850_{qnum:03d}", question_type, question, [claim], pmid_to_article))
                used_questions.add(normalize_question(question))
                qnum += 1
                return True
            claim = unused_single_claim()
        return False

    for question_type in ("description", "evidence_lookup", "reason"):
        needed = max(0, target_counts[question_type] - existing_counts.get(question_type, 0))
        for _ in range(needed):
            if len(items) >= size or not add_single(question_type):
                break

    by_outcome: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        if claim["claim_id"] not in used_claim_ids:
            by_outcome[claim["object_name"]].append(claim)

    comparison_groups = []
    for outcome, group in by_outcome.items():
        unique_subjects = {}
        for claim in sorted(
            group,
            key=lambda c: (-int(c.get("evidence_count") or 0), -float(c.get("confidence_score") or 0)),
        ):
            unique_subjects.setdefault(claim["subject_name"], claim)
        if len(unique_subjects) >= 2:
            comparison_groups.append((outcome, list(unique_subjects.values())[:3]))
    rng.shuffle(comparison_groups)

    for outcome, group in comparison_groups:
        if len(items) >= size:
            break
        subjects = [humanize(claim["subject_name"]) for claim in group]
        question = (
            f"Compare the evidence for {', '.join(subjects[:-1])} and {subjects[-1]} "
            f"with respect to {humanize(outcome)}."
        )
        if normalize_question(question) in used_questions:
            continue
        items.append(make_item(f"qa850_{qnum:03d}", "comparison", question, group, pmid_to_article))
        used_questions.add(normalize_question(question))
        used_claim_ids.update(claim["claim_id"] for claim in group)
        qnum += 1

    if len(items) < size:
        raise RuntimeError(f"Only generated {len(items)} unique benchmark items; requested {size}")

    return {
        "benchmark_id": f"food_ai_qa_850_seed_v{existing.get('schema_version', 1) + 1}",
        "created_from": {
            "extraction": str(extraction_path),
            "corpus": str(corpus_path),
            "extended_from": existing.get("benchmark_id"),
        },
        "seed": seed,
        "size": len(items),
        "schema_version": existing.get("schema_version", 1) + 1,
        "description": (
            "Extended fixed QA benchmark for Food-AI 850-graph retrieval and agent recall. "
            "The first items are preserved from the prior benchmark; appended questions avoid "
            "duplicate question text and previously used gold claims."
        ),
        "items": items[:size],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction", type=Path, default=DEFAULT_EXTRACTION)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260427)
    parser.add_argument(
        "--extend-from",
        type=Path,
        help="Existing benchmark JSON to preserve as a prefix before adding non-duplicate questions.",
    )
    args = parser.parse_args()

    extraction = load_json(args.extraction)
    corpus = load_json(args.corpus)
    if args.extend_from:
        existing = load_json(args.extend_from)
        benchmark = build_extended_benchmark(
            extraction,
            corpus,
            args.size,
            args.seed,
            existing,
            args.extraction,
            args.corpus,
        )
    else:
        benchmark = build_benchmark(
            extraction,
            corpus,
            args.size,
            args.seed,
            args.extraction,
            args.corpus,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(benchmark, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(benchmark['items'])} benchmark items to {args.output}")


if __name__ == "__main__":
    main()
