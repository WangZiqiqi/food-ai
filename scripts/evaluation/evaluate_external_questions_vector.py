#!/usr/bin/env python3
"""Evaluate external-style food science questions against graph-retrieved claims."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from food_ai.pydantic_ai_client import create_poe_model


DEFAULT_QUESTIONS = Path("data/evaluation/external_food_science_questions_template_40.csv")
DEFAULT_EXTRACTION = Path("data/processed/final_graph/food_ai_graph.json")
DEFAULT_JSONL = Path("data/evaluation/external_food_science_questions_vector_review_40.jsonl")
DEFAULT_SUMMARY = Path("data/evaluation/external_food_science_questions_vector_review_40_summary.md")


class ExternalQuestionDecision(BaseModel):
    answerability: Literal["answerable", "partial", "not_answerable"]
    usefulness: Literal["useful", "partially_useful", "not_useful"]
    should_abstain: bool
    supporting_claim_ids: list[str] = Field(default_factory=list)
    supporting_pmids: list[str] = Field(default_factory=list)
    reason: str


SYSTEM_PROMPT = """You evaluate whether retrieved Food-AI graph claims answer an external food-science question.

Be conservative:
- answerable: retrieved claims directly address the question with subject/outcome match.
- partial: retrieved claims are adjacent or cover only part of a comparison.
- not_answerable: retrieved claims do not directly address the question.
- should_abstain=true when the graph evidence is absent or only adjacent.
- Cite only claim_ids and PMIDs present in the provided retrieved candidates.
- Do not use outside knowledge.
"""


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def lexical_score(query: str, claim: dict[str, Any]) -> float:
    q_tokens = Counter(tokens(query))
    text = " ".join(
        str(part or "")
        for part in (
            claim.get("claim_text"),
            claim.get("subject_name"),
            claim.get("object_name"),
            claim.get("direction"),
        )
    )
    c_tokens = Counter(tokens(text))
    if not q_tokens or not c_tokens:
        return 0.0
    overlap = sum(min(count, c_tokens.get(tok, 0)) for tok, count in q_tokens.items())
    q_norm = sum(v * v for v in q_tokens.values()) ** 0.5
    c_norm = sum(v * v for v in c_tokens.values()) ** 0.5
    score = overlap / (q_norm * c_norm) if q_norm and c_norm else 0.0
    subject = str(claim.get("subject_name") or "").replace("_", " ").lower()
    outcome = str(claim.get("object_name") or "").replace("_", " ").lower()
    q_lower = query.lower()
    if subject and subject in q_lower:
        score += 0.25
    if outcome and outcome in q_lower:
        score += 0.25
    return score


def retrieve_claims(question: str, claims: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    ranked = sorted(
        ((lexical_score(question, claim), claim) for claim in claims),
        key=lambda pair: pair[0],
        reverse=True,
    )
    return [
        {
            "rank": idx,
            "score": round(score, 4),
            "claim_id": claim.get("claim_id"),
            "claim_text": claim.get("claim_text"),
            "subject_name": claim.get("subject_name"),
            "object_name": claim.get("object_name"),
            "direction": claim.get("direction"),
            "evidence_count": claim.get("evidence_count"),
            "pmids": sorted({str(ev.get("pmid")) for ev in claim.get("evidence_list", []) if ev.get("pmid")}),
            "snippet": next(
                (
                    ev.get("evidence_snippet")
                    for ev in claim.get("evidence_list", [])
                    if ev.get("evidence_snippet")
                ),
                "",
            ),
        }
        for idx, (score, claim) in enumerate(ranked[:top_k], start=1)
    ]


def make_prompt(question: dict[str, str], retrieved: list[dict[str, Any]]) -> str:
    candidates = json.dumps(retrieved, ensure_ascii=False, indent=2)
    return f"""External question:
- id: {question.get("question_id")}
- type: {question.get("question_type")}
- question: {question.get("question")}

Retrieved graph candidates:
{candidates}

Judge whether the retrieved claims answer the question."""


def build_agent(model: str) -> Agent:
    return Agent(
        create_poe_model(model),
        output_type=ExternalQuestionDecision,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )


def load_completed(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                done.add(str(json.loads(line).get("question_id")))
    return done


def summarize(rows: list[dict[str, Any]]) -> str:
    answerability = Counter(row.get("answerability") for row in rows)
    usefulness = Counter(row.get("usefulness") for row in rows)
    abstain = Counter(bool(row.get("should_abstain")) for row in rows)
    by_type: dict[str, Counter] = {}
    for row in rows:
        by_type.setdefault(row.get("question_type", "missing"), Counter()).update([row.get("answerability")])
    lines = [
        "# External Food-Science Question Vector Review",
        "",
        f"Generated: `{datetime.now().isoformat(timespec='seconds')}`",
        f"Count: `{len(rows)}`",
        "",
        "## Answerability",
        "| Label | Count |",
        "| --- | ---: |",
    ]
    for label in ("answerable", "partial", "not_answerable"):
        lines.append(f"| {label} | {answerability.get(label, 0)} |")
    lines.extend(["", "## Usefulness", "| Label | Count |", "| --- | ---: |"])
    for label in ("useful", "partially_useful", "not_useful"):
        lines.append(f"| {label} | {usefulness.get(label, 0)} |")
    lines.extend(["", "## Abstention", "| Should abstain | Count |", "| --- | ---: |"])
    for label in (True, False):
        lines.append(f"| {label} | {abstain.get(label, 0)} |")
    lines.extend(["", "## By Question Type", "| Type | Answerable | Partial | Not answerable |", "| --- | ---: | ---: | ---: |"])
    for qtype, counts in sorted(by_type.items()):
        lines.append(
            f"| {qtype} | {counts.get('answerable', 0)} | {counts.get('partial', 0)} | {counts.get('not_answerable', 0)} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--extraction", type=Path, default=DEFAULT_EXTRACTION)
    parser.add_argument("--output-jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--model", default="minimax-m2.7")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.overwrite and args.output_jsonl.exists():
        args.output_jsonl.unlink()

    claims = load_json(args.extraction).get("merged_claims", [])
    questions = read_csv(args.questions)
    completed = load_completed(args.output_jsonl)
    agent = build_agent(args.model)

    processed = 0
    for question in questions:
        qid = question.get("question_id")
        if not qid or qid in completed:
            continue
        retrieved = retrieve_claims(question.get("question", ""), claims, args.top_k)
        decision = agent.run_sync(make_prompt(question, retrieved), model_settings={"temperature": 0}).output
        row = {
            "question_id": qid,
            "question": question.get("question"),
            "question_type": question.get("question_type"),
            "retrieved": retrieved,
            "model": args.model,
            "reviewed_at": datetime.now().isoformat(timespec="seconds"),
            **decision.model_dump(),
        }
        append_jsonl(args.output_jsonl, row)
        processed += 1
        print(f"{qid} {decision.answerability} useful={decision.usefulness} abstain={decision.should_abstain}", flush=True)
        if args.limit and processed >= args.limit:
            break

    rows = []
    if args.output_jsonl.exists():
        with args.output_jsonl.open("r", encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.summary_md.write_text(summarize(rows), encoding="utf-8")
    print(f"wrote {args.output_jsonl}")
    print(f"wrote {args.summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
