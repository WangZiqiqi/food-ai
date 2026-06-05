#!/usr/bin/env python3
"""Select PubMed expansion candidates with pydantic-ai corpus suitability labels."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent

from food_ai.pydantic_ai_client import create_poe_model


TODAY = "2026-04-25"


TOPIC = """We are building a knowledge graph and agent QA corpus about fermented foods, probiotics/synbiotics/postbiotics, microbes/strains, bioactive compounds, mechanisms, and human health outcomes.

Include articles if their title/abstract can support extraction of useful claims for this KG. Strong candidates are human interventions, RCTs, clinical trials, observational human studies, systematic reviews/meta-analyses, or high-scope reviews directly about fermented foods/probiotics and health/microbiome outcomes.

Current corpus construction is abstract-only. Exclude or mark uncertain when the abstract is missing or too thin for claim extraction, even if the title is topically relevant.

Exclude animal-only, in-vitro-only, aquaculture/livestock/feed studies, food processing/chemistry without health outcome, bibliometrics, patents, and unrelated disease/drug studies."""


class CorpusSuitability(BaseModel):
    pmid: str = Field(description="Candidate PMID")
    decision: Literal["include", "exclude", "uncertain"] = Field(description="Whether this article should be included in the KG corpus")
    confidence: float = Field(ge=0.0, le=1.0)
    article_type: Literal[
        "human_intervention",
        "human_observational",
        "systematic_review",
        "narrative_review",
        "mechanistic_human_relevant",
        "animal",
        "in_vitro",
        "food_processing_only",
        "other",
    ]
    directness: Literal["direct", "supporting", "out_of_scope"]
    abstract_usable: bool = Field(description="Whether the abstract contains enough information for claim extraction")
    reason: str

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> Any:
        if isinstance(value, (int, float)) and value > 1:
            return value / 100
        return value


class CorpusSuitabilityBatch(BaseModel):
    decisions: list[CorpusSuitability]


def build_agent(model: str) -> Agent:
    return Agent(
        create_poe_model(model),
        output_type=CorpusSuitabilityBatch,
        retries=2,
        system_prompt="""You are screening PubMed papers for a fermented-food/probiotic knowledge graph corpus.

Return one strict structured decision for each candidate PMID. Be conservative: include only when the title/abstract is clearly useful for extracting claims about fermented foods/probiotics/synbiotics/postbiotics, microbes/strains, mechanisms, or human health/microbiome outcomes.

Because the corpus is abstract-only, include requires abstract_usable=true. Reviews can be included when directly relevant, especially systematic reviews/meta-analyses, but if a review abstract is too generic and has no extractable findings, mark uncertain or exclude.
""",
    )


def candidate_block(candidate: dict[str, Any]) -> str:
    publication_types = candidate.get("publication_types", [])
    if publication_types and isinstance(publication_types[0], dict):
        pub_types = [item.get("name", "") for item in publication_types]
    else:
        pub_types = publication_types
    return f"""
PMID: {candidate.get('pmid')}
Title: {candidate.get('title')}
Study type by rule score: {candidate.get('study_type')}
Publication types: {pub_types}
Rule relevance score: {candidate.get('relevance_score')}
Rule quality score: {candidate.get('overall_quality')}
Expansion score: {candidate.get('expansion_score')}
Source queries: {candidate.get('source_queries')}
Abstract:
{(candidate.get('abstract') or 'NO ABSTRACT')[:350]}
"""


def batch_prompt(candidates: list[dict[str, Any]]) -> str:
    blocks = "\n---\n".join(candidate_block(candidate) for candidate in candidates)
    return f"""Corpus topic and inclusion criteria:
{TOPIC}

Return exactly one decision for each candidate PMID below.

Candidates:
{blocks}
"""


def read_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    labels: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return labels
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        labels[str(row["pmid"])] = row
    return labels


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def count_accepted(
    candidates: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    min_confidence: float,
    needed: int,
) -> int:
    accepted = 0
    for candidate in candidates:
        label = labels.get(str(candidate.get("pmid")))
        if not label:
            continue
        if (
            label["decision"] == "include"
            and label["confidence"] >= min_confidence
            and label.get("abstract_usable") is True
            and label.get("directness") != "out_of_scope"
        ):
            accepted += 1
            if accepted >= needed:
                return accepted
    return accepted


def selected_article_row(candidate: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    row = {
        "pmid": candidate.get("pmid"),
        "title": candidate.get("title"),
        "journal": candidate.get("journal", "Unknown"),
        "year": candidate.get("pub_date") or candidate.get("year") or "Unknown",
        "study_type": candidate.get("study_type", "Other/Unknown"),
        "quality_score": candidate.get("overall_quality", candidate.get("quality_score", 0)),
        "relevance_score": candidate.get("relevance_score", 0),
        "source": "pubmed_expansion_llm_20260425",
        "expansion_score": candidate.get("expansion_score"),
        "selection_reasons": candidate.get("selection_reasons", []),
        "source_queries": candidate.get("source_queries", []),
        "has_pmcid": candidate.get("has_pmcid", False),
        "is_review": candidate.get("is_review", False),
        "is_trial": candidate.get("is_trial", False),
    }
    row.update(extra)
    return row


def label_batch(
    agent: Agent,
    pending_batch: list[tuple[int, dict[str, Any]]],
    labels: dict[str, dict[str, Any]],
    args: argparse.Namespace,
) -> int:
    indexes = {str(candidate.get("pmid")): index for index, candidate in pending_batch}
    titles = {str(candidate.get("pmid")): candidate.get("title") for _, candidate in pending_batch}
    output = agent.run_sync(
        batch_prompt([candidate for _, candidate in pending_batch]),
        model_settings={"temperature": 0},
    ).output

    added = 0
    for decision in output.decisions:
        pmid = str(decision.pmid)
        if pmid not in indexes or pmid in labels:
            continue
        row = {
            "pmid": pmid,
            "title": titles.get(pmid),
            "model": args.model,
            "labeled_at": datetime.now().isoformat(),
            "rank": indexes[pmid],
            **decision.model_dump(),
        }
        append_jsonl(args.labels, row)
        labels[pmid] = row
        added += 1
        print(
            f"label_added={added} rank={row['rank']} pmid={pmid} "
            f"decision={row['decision']} conf={row['confidence']} type={row['article_type']}",
            flush=True,
        )

    missing = sorted(set(indexes) - {str(decision.pmid) for decision in output.decisions})
    if missing:
        print(f"missing_decisions={missing}", flush=True)
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM-label and select PubMed expansion candidates")
    parser.add_argument("--candidates", type=Path, default=Path(f"data/candidate_pool/pubmed_expansion_candidates_{TODAY}.json"))
    parser.add_argument("--selected", type=Path, default=Path("data/processed/selected_141_quality.json"))
    parser.add_argument("--target-total", type=int, default=300)
    parser.add_argument("--model", default="minimax-m2.7")
    parser.add_argument("--labels", type=Path, default=Path(f"data/candidate_pool/pubmed_expansion_llm_labels_{TODAY}.jsonl"))
    parser.add_argument("--audit", type=Path, default=Path(f"data/candidate_pool/pubmed_expansion_llm_audit_{TODAY}.json"))
    parser.add_argument("--output", type=Path, default=Path(f"data/processed/selected_300_quality_llm_proposed_{TODAY}.json"))
    parser.add_argument("--min-confidence", type=float, default=0.60)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--max-labels", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--stop-when-accepted", action="store_true")
    args = parser.parse_args()

    selected_data = json.loads(args.selected.read_text())
    selected_articles = selected_data.get("articles", [])
    existing_pmids = {str(article.get("pmid")) for article in selected_articles if article.get("pmid")}
    needed = max(0, args.target_total - len(selected_articles))

    raw = json.loads(args.candidates.read_text())
    candidates = [item for item in raw.get("candidates", []) if str(item.get("pmid")) not in existing_pmids]
    candidates.sort(
        key=lambda item: (
            item.get("expansion_score", 0),
            item.get("overall_quality", 0),
            item.get("relevance_score", 0),
        ),
        reverse=True,
    )

    labels = read_jsonl(args.labels)
    agent = build_agent(args.model)
    newly_labeled = 0

    pending_batch: list[tuple[int, dict[str, Any]]] = []
    for index, candidate in enumerate(candidates, start=1):
        if args.stop_when_accepted and count_accepted(candidates, labels, args.min_confidence, needed) >= needed:
            break
        if str(candidate.get("pmid")) in labels:
            continue
        if args.max_labels is not None and newly_labeled >= args.max_labels:
            break
        remaining = None if args.max_labels is None else args.max_labels - newly_labeled - len(pending_batch)
        if remaining is not None and remaining <= 0:
            break
        pending_batch.append((index, candidate))
        if len(pending_batch) < args.batch_size:
            continue

        batch_new = label_batch(agent, pending_batch, labels, args)
        newly_labeled += batch_new
        pending_batch = []
        accepted_so_far = count_accepted(candidates, labels, args.min_confidence, needed)
        print(f"progress labeled={len(labels)} accepted_so_far={accepted_so_far}/{needed}", flush=True)
        time.sleep(args.sleep)

    if pending_batch and (args.max_labels is None or newly_labeled < args.max_labels):
        if args.max_labels is not None:
            pending_batch = pending_batch[: max(0, args.max_labels - newly_labeled)]
        newly_labeled += label_batch(agent, pending_batch, labels, args)

    accepted = []
    excluded = []
    uncertain = []
    for candidate in candidates:
        label = labels.get(str(candidate.get("pmid")))
        if not label:
            continue
        if (
            label["decision"] == "include"
            and label["confidence"] >= args.min_confidence
            and label.get("abstract_usable") is True
            and label.get("directness") != "out_of_scope"
        ):
            accepted.append((candidate, label))
        elif label["decision"] == "uncertain":
            uncertain.append((candidate, label))
        else:
            excluded.append((candidate, label))

    accepted = accepted[:needed]
    proposed_articles = [{**article, "source": article.get("source", "selected_141")} for article in selected_articles]
    for candidate, label in accepted:
        proposed_articles.append(
            selected_article_row(
                candidate,
                {
                    "llm_decision": label["decision"],
                    "llm_confidence": label["confidence"],
                    "llm_article_type": label["article_type"],
                    "llm_directness": label["directness"],
                    "llm_abstract_usable": label["abstract_usable"],
                    "llm_reason": label["reason"],
                },
            )
        )

    study_counter = Counter(article.get("study_type", "Unknown") for article in proposed_articles)
    label_counter = Counter(label["decision"] for label in labels.values())
    article_type_counter = Counter(label["article_type"] for _, label in accepted)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "total": len(proposed_articles),
                "previous_total": len(selected_articles),
                "new_count": len(accepted),
                "target_total": args.target_total,
                "model": args.model,
                "selection_criteria": {
                    "base": str(args.selected),
                    "raw_candidates": str(args.candidates),
                    "labels": str(args.labels),
                    "min_confidence": args.min_confidence,
                    "method": "PubMed strict query expansion + rule score + pydantic-ai corpus suitability include decision",
                },
                "study_type_counts": dict(study_counter),
                "new_article_type_counts": dict(article_type_counter),
                "articles": proposed_articles,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(
        json.dumps(
            {
                "created_at": datetime.now().isoformat(),
                "raw_candidates": str(args.candidates),
                "labels": str(args.labels),
                "output": str(args.output),
                "existing_count": len(selected_articles),
                "candidate_count": len(candidates),
                "labeled_count": len(labels),
                "newly_labeled": newly_labeled,
                "accepted_count": len(accepted),
                "final_total": len(proposed_articles),
                "target_total": args.target_total,
                "label_counts": dict(label_counter),
                "accepted_article_type_counts": dict(article_type_counter),
                "top_accepted_pmids": [candidate.get("pmid") for candidate, _ in accepted[:50]],
                "top_uncertain_pmids": [candidate.get("pmid") for candidate, _ in uncertain[:50]],
                "top_excluded_pmids": [candidate.get("pmid") for candidate, _ in excluded[:50]],
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    print(f"labels={args.labels}")
    print(f"audit={args.audit}")
    print(f"output={args.output}")
    print(f"candidate_count={len(candidates)} labeled={len(labels)} accepted={len(accepted)} final_total={len(proposed_articles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
