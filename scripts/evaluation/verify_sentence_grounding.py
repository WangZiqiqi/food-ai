#!/usr/bin/env python3
"""Verify whether evidence sentences support extracted claims.

This script is intentionally evaluation-only: it does not modify the graph.
It uses pydantic-ai structured output through the shared Poe model helper.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_ai import Agent

from food_ai.pydantic_ai_client import create_poe_model


DEFAULT_AUDIT = Path("data/evaluation/manual_claim_audit_100_post_backfill_completed.csv")
DEFAULT_ARTICLES = Path("data/processed/selected_850_quality_llm_abstract_complete_2026-04-26.json")
DEFAULT_JSONL = Path("data/evaluation/sentence_grounding_verifier_100.jsonl")
DEFAULT_SUMMARY = Path("data/evaluation/sentence_grounding_verifier_100_summary.md")


class SentenceGroundingDecision(BaseModel):
    """Structured LLM judgement for one claim/evidence pair."""

    support_label: Literal["supports", "contradicts", "insufficient"] = Field(
        description=(
            "Use supports only when one selected sentence explicitly supports the "
            "subject, outcome, and claimed direction. Use contradicts when the "
            "sentence/paper indicates the opposite or no significant effect. "
            "Use insufficient when the evidence is related but does not prove the claim."
        )
    )
    direction_label: Literal["positive", "negative", "neutral", "unclear"]
    effect_direction: Literal[
        "increased",
        "decreased",
        "changed",
        "no_significant_effect",
        "associated",
        "mixed",
        "unclear",
    ] = Field(
        description=(
            "Measured outcome direction supported by the best sentence. This is "
            "the literal outcome change, not whether the change is beneficial."
        )
    )
    health_interpretation: Literal["beneficial", "harmful", "neutral", "mixed", "unclear"] = Field(
        description=(
            "Health/domain interpretation of the effect. Use unclear when the "
            "abstract sentence does not justify a health meaning."
        )
    )
    direction_supported: Literal["yes", "no", "unclear"] = Field(
        description=(
            "Whether the selected sentence supports the original claimed_direction. "
            "Use unclear when no sufficient sentence is available."
        )
    )
    best_sentence: str | None = Field(
        default=None,
        description="A verbatim sentence from the abstract/current snippet, or null if none supports the claim.",
    )
    best_sentence_id: str | None = Field(
        default=None,
        description="Use C for the current snippet or A1, A2, ... for abstract sentences; null if none.",
    )
    best_sentence_source: Literal["current_snippet", "abstract", "none"]
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(description="Brief reason for the judgement.")

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> Any:
        if isinstance(value, (int, float)) and value > 1:
            return value / 100
        return value

    @model_validator(mode="after")
    def validate_sentence_consistency(self) -> "SentenceGroundingDecision":
        has_sentence = bool((self.best_sentence or "").strip())
        has_sentence_id = bool((self.best_sentence_id or "").strip())
        if self.support_label == "insufficient" and self.best_sentence_source != "none":
            self.best_sentence = None
            self.best_sentence_id = None
            self.best_sentence_source = "none"
            self.direction_supported = "unclear"
        if not (has_sentence or has_sentence_id) and self.best_sentence_source != "none":
            self.best_sentence_source = "none"
        return self


SYSTEM_PROMPT = """You verify sentence-level grounding for PubMed-derived food/probiotic knowledge graph claims.

Be strict and conservative:
- A sentence supports a claim only if it explicitly supports the subject, outcome, and claimed direction.
- Study aims, background, methods, or generic statements are insufficient.
- "No significant effect/difference" is neutral, not negative.
- Interpret the original claimed_direction as the direction of the named outcome itself, not as a health value judgement.
  Example: "reduced LDL cholesterol" supports claimed_direction=negative for the LDL cholesterol outcome, with health_interpretation=beneficial.
  Example: "reduced adverse events" supports claimed_direction=negative for the adverse events outcome, with health_interpretation=beneficial.
  Example: "reduced child mortality" supports claimed_direction=negative for the child mortality outcome, not positive.
  Example: "inflammation plays a role in atherosclerosis" supports effect_direction=associated and health_interpretation=harmful, but it does not support claimed_direction=negative.
  Example: "improves depression scores" is ambiguous unless the sentence makes clear whether scores increased or decreased; use unclear if the measured direction is not explicit.
- Separate the measured outcome direction from the health/domain interpretation:
  LDL cholesterol decreased => effect_direction=decreased and health_interpretation=beneficial.
  Adverse events decreased => effect_direction=decreased and health_interpretation=beneficial.
  Gut microbiota changed without an explicit improvement => effect_direction=changed and health_interpretation=unclear.
  No significant difference/effect => effect_direction=no_significant_effect and health_interpretation=neutral.
- Prefer selecting best_sentence_id: C for the current snippet, or A1/A2/... for an abstract sentence.
- You may also copy best_sentence verbatim from the provided current snippet or abstract sentences.
- If no single provided sentence supports the complete claim, set support_label to insufficient,
  best_sentence_id to null, best_sentence to null, best_sentence_source to none,
  and direction_supported to unclear.
- If a sentence supports the subject and outcome but not the original claimed_direction,
  set support_label to insufficient and direction_supported to no. You may still provide
  effect_direction and health_interpretation if they are clear from the sentence.
- Never set support_label to supports unless the original claimed_direction is explicitly supported
  by one exact provided sentence identified by best_sentence_id.
- Use contradicts only when the selected sentence clearly supports the opposite direction or
  no significant effect for the same subject and outcome.
"""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def article_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("articles", "results", "papers", "selected"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    raise ValueError(f"could not find article list in {type(data).__name__}")


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", text)
    return [part.strip() for part in parts if len(part.strip()) >= 20]


def load_completed(path: Path) -> set[str]:
    if not path.exists():
        return set()
    completed: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            audit_id = row.get("audit_id")
            if audit_id:
                completed.add(str(audit_id))
    return completed


def make_prompt(row: dict[str, str], article: dict[str, Any] | None) -> tuple[str, dict[str, str]]:
    abstract = article.get("abstract", "") if article else ""
    sentences = split_sentences(abstract)
    sentence_map = {f"A{idx + 1}": sentence for idx, sentence in enumerate(sentences[:25])}
    sentence_block = "\n".join(f"[A{idx + 1}] {sentence}" for idx, sentence in enumerate(sentences[:25]))
    if not sentence_block:
        sentence_block = "No abstract sentences available."
    current_snippet = row.get("primary_evidence_snippet") or "EMPTY"
    if row.get("primary_evidence_snippet"):
        sentence_map["C"] = row["primary_evidence_snippet"]
    return f"""Claim:
- claim_id: {row.get("claim_id")}
- claim_text: {row.get("claim_text")}
- subject_name: {row.get("subject_name")}
- subject_type: {row.get("subject_type")}
- outcome_name: {row.get("object_name")}
- outcome_type: {row.get("object_type")}
- claimed_direction: {row.get("direction")}
- PMID: {row.get("primary_pmid")}
- study_type: {row.get("primary_study_type")}

Current evidence snippet:
[C] {current_snippet}

Article title:
{article.get("title", "Unknown") if article else "Unknown"}

Abstract sentences:
{sentence_block}

Return a strict sentence-level grounding judgement.""", sentence_map


def resolve_best_sentence(decision: SentenceGroundingDecision, sentence_map: dict[str, str]) -> None:
    sentence_id = (decision.best_sentence_id or "").strip().upper()
    if not sentence_id:
        mentioned = []
        for match in re.findall(r"\b(?:sentence\s+)?(C|A\d{1,2})\b", decision.reason, flags=re.IGNORECASE):
            candidate = match.upper()
            if candidate in sentence_map and candidate not in mentioned:
                mentioned.append(candidate)
        if len(mentioned) == 1:
            sentence_id = mentioned[0]
        elif not mentioned and decision.best_sentence_source == "current_snippet" and "C" in sentence_map:
            sentence_id = "C"
    if sentence_id and sentence_id in sentence_map:
        decision.best_sentence_id = sentence_id
        decision.best_sentence = sentence_map[sentence_id]
        decision.best_sentence_source = "current_snippet" if sentence_id == "C" else "abstract"


def normalize_grounding(decision: SentenceGroundingDecision) -> None:
    has_sentence = bool((decision.best_sentence or "").strip())
    if decision.support_label == "supports" and decision.direction_supported != "yes":
        decision.support_label = "insufficient"
        decision.best_sentence = None
        decision.best_sentence_id = None
        decision.best_sentence_source = "none"
        decision.confidence = min(decision.confidence, 0.5)
        decision.reason = (
            decision.reason.rstrip()
            + " Downgraded because direction_supported was not yes."
        )
    if decision.support_label in {"supports", "contradicts"} and not has_sentence:
        decision.support_label = "insufficient"
        decision.direction_label = "unclear"
        decision.effect_direction = "unclear"
        decision.health_interpretation = "unclear"
        decision.direction_supported = "unclear"
        decision.best_sentence = None
        decision.best_sentence_id = None
        decision.best_sentence_source = "none"
        decision.confidence = min(decision.confidence, 0.3)
        decision.reason = (
            decision.reason.rstrip()
            + " Downgraded because no single provided sentence could be resolved."
        )
    if decision.support_label == "insufficient":
        decision.best_sentence = None
        decision.best_sentence_id = None
        decision.best_sentence_source = "none"
        decision.direction_supported = "unclear"


def build_agent(model: str) -> Agent:
    return Agent(
        create_poe_model(model),
        output_type=SentenceGroundingDecision,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )


def summarize(rows: list[dict[str, Any]]) -> str:
    support_counts = Counter(row.get("support_label") for row in rows)
    direction_counts = Counter(row.get("direction_label") for row in rows)
    effect_counts = Counter(row.get("effect_direction") for row in rows)
    health_counts = Counter(row.get("health_interpretation") for row in rows)
    direction_supported_counts = Counter(row.get("direction_supported") for row in rows)
    source_counts = Counter(row.get("best_sentence_source") for row in rows)
    human_map = {"yes": "supports", "no": "not_supports", "unclear": "unclear"}
    cross = Counter(
        (
            human_map.get(str(row.get("human_snippet_supports_claim", "")).lower(), "missing"),
            row.get("support_label"),
        )
        for row in rows
    )

    lines = [
        "# Sentence Grounding Verifier Summary",
        "",
        f"Generated: `{datetime.now().isoformat(timespec='seconds')}`",
        f"Count: `{len(rows)}`",
        "",
        "## Support Labels",
        "| Label | Count |",
        "| --- | ---: |",
    ]
    for label in ("supports", "contradicts", "insufficient"):
        lines.append(f"| {label} | {support_counts.get(label, 0)} |")

    lines.extend(["", "## Direction Labels", "| Label | Count |", "| --- | ---: |"])
    for label in ("positive", "negative", "neutral", "unclear"):
        lines.append(f"| {label} | {direction_counts.get(label, 0)} |")

    lines.extend(["", "## Measured Effect Directions", "| Label | Count |", "| --- | ---: |"])
    for label in (
        "increased",
        "decreased",
        "changed",
        "no_significant_effect",
        "associated",
        "mixed",
        "unclear",
    ):
        lines.append(f"| {label} | {effect_counts.get(label, 0)} |")

    lines.extend(["", "## Health Interpretations", "| Label | Count |", "| --- | ---: |"])
    for label in ("beneficial", "harmful", "neutral", "mixed", "unclear"):
        lines.append(f"| {label} | {health_counts.get(label, 0)} |")

    lines.extend(["", "## Original Direction Supported", "| Label | Count |", "| --- | ---: |"])
    for label in ("yes", "no", "unclear"):
        lines.append(f"| {label} | {direction_supported_counts.get(label, 0)} |")

    lines.extend(["", "## Best Sentence Source", "| Source | Count |", "| --- | ---: |"])
    for label in ("current_snippet", "abstract", "none"):
        lines.append(f"| {label} | {source_counts.get(label, 0)} |")

    lines.extend(
        [
            "",
            "## Human Audit vs Verifier",
            "| Human snippet label | Verifier label | Count |",
            "| --- | --- | ---: |",
        ]
    )
    for (human, verifier), count in sorted(cross.items()):
        lines.append(f"| {human} | {verifier} | {count} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify sentence-level evidence grounding for audit claims.")
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--articles", type=Path, default=DEFAULT_ARTICLES)
    parser.add_argument("--output-jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--model", default="minimax-m2.7")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.overwrite and args.output_jsonl.exists():
        args.output_jsonl.unlink()

    audit_rows = read_csv(args.audit)
    articles = {
        str(article.get("pmid")): article
        for article in article_records(load_json(args.articles))
        if article.get("pmid") is not None
    }
    completed = load_completed(args.output_jsonl)
    agent = build_agent(args.model)

    processed = 0
    for row in audit_rows:
        audit_id = row.get("audit_id")
        if not audit_id or audit_id in completed:
            continue
        article = articles.get(str(row.get("primary_pmid")))
        prompt, sentence_map = make_prompt(row, article)
        decision = agent.run_sync(
            prompt,
            model_settings={"temperature": args.temperature},
        ).output
        resolve_best_sentence(decision, sentence_map)
        normalize_grounding(decision)
        output_row = {
            "audit_id": audit_id,
            "claim_id": row.get("claim_id"),
            "claim_text": row.get("claim_text"),
            "claimed_direction": row.get("direction"),
            "primary_pmid": row.get("primary_pmid"),
            "human_direction_correct": row.get("audit_direction_correct"),
            "human_snippet_supports_claim": row.get("audit_snippet_supports_claim"),
            "human_notes": row.get("audit_notes"),
            "model": args.model,
            "verified_at": datetime.now().isoformat(timespec="seconds"),
            **decision.model_dump(),
        }
        append_jsonl(args.output_jsonl, output_row)
        processed += 1
        print(
            f"verified {audit_id} claim={row.get('claim_id')} "
            f"support={decision.support_label} direction={decision.direction_label}",
            flush=True,
        )
        if args.limit and processed >= args.limit:
            break

    result_rows = []
    if args.output_jsonl.exists():
        with args.output_jsonl.open("r", encoding="utf-8") as handle:
            result_rows = [json.loads(line) for line in handle if line.strip()]
    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.summary_md.write_text(summarize(result_rows), encoding="utf-8")
    print(f"wrote {args.output_jsonl}")
    print(f"wrote {args.summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
