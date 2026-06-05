#!/usr/bin/env python3
"""Fill a 30-row double-reviewer audit sheet with two conservative LLM review passes."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from food_ai.pydantic_ai_client import create_poe_model


DEFAULT_INPUT = Path("data/evaluation/manual_claim_audit_double_reviewer_sample_30.csv")
DEFAULT_OUTPUT = Path("data/evaluation/manual_claim_audit_double_reviewer_completed_30.csv")


class AuditDecision(BaseModel):
    subject_correct: Literal["yes", "no", "unclear"]
    outcome_correct: Literal["yes", "no", "unclear"]
    direction_correct: Literal["yes", "no", "unclear"]
    snippet_supports_claim: Literal["yes", "no", "unclear"]
    pmid_traceable: Literal["yes", "no", "unclear"]
    notes: str = Field(description="Short reason for the labels.")


SYSTEM_PROMPTS = {
    "reviewer1": """You are reviewer 1 for a conservative food-science claim audit.
Judge only what is visible in the claim text and evidence sentence.
Use yes/no/unclear. Use unclear when the evidence sentence is missing or related but not decisive.
For direction_correct, judge the direction of the named outcome itself:
reduced LDL/adverse events/mortality supports negative for that outcome;
increased/improved beneficial properties can support positive;
no significant difference supports neutral.
Do not give credit for broad background, study aims, or trial design sentences.""",
    "reviewer2": """You are reviewer 2 for an independent conservative food-science claim audit.
Be slightly stricter than reviewer 1 about snippet support and effect direction.
Use yes/no/unclear. Use no when the snippet points to the opposite direction.
Use unclear when the snippet is absent, only mentions design, or supports the topic but not the exact direction.
PMID traceable means the row has a plausible PMID provenance, not that the claim is fully correct.""",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_prompt(row: dict[str, str]) -> str:
    return f"""Audit this extracted claim.

Claim:
- claim_id: {row.get("claim_id")}
- claim_text: {row.get("claim_text")}
- subject_name: {row.get("subject_name")}
- subject_type: {row.get("subject_type")}
- outcome_name: {row.get("object_name")}
- outcome_type: {row.get("object_type")}
- claimed_direction: {row.get("direction")}
- effect_direction field: {row.get("effect_direction") or "missing"}
- health_interpretation field: {row.get("health_interpretation") or "missing"}
- primary_pmid: {row.get("primary_pmid")}

Evidence sentence:
{row.get("primary_evidence_snippet") or "EMPTY"}

Return labels for subject correctness, outcome correctness, direction correctness,
snippet support for the whole claim, PMID traceability, and a brief note."""


def build_agent(model: str, reviewer: str) -> Agent:
    return Agent(
        create_poe_model(model),
        output_type=AuditDecision,
        system_prompt=SYSTEM_PROMPTS[reviewer],
        retries=2,
    )


def apply_decision(row: dict[str, str], prefix: str, decision: AuditDecision) -> None:
    row[f"{prefix}_subject_correct"] = decision.subject_correct
    row[f"{prefix}_outcome_correct"] = decision.outcome_correct
    row[f"{prefix}_direction_correct"] = decision.direction_correct
    row[f"{prefix}_snippet_supports_claim"] = decision.snippet_supports_claim
    row[f"{prefix}_pmid_traceable"] = decision.pmid_traceable
    row[f"{prefix}_notes"] = decision.notes


def resolve(row: dict[str, str]) -> None:
    fields = [
        "subject_correct",
        "outcome_correct",
        "direction_correct",
        "snippet_supports_claim",
        "pmid_traceable",
    ]
    notes = []
    for field in fields:
        left = row.get(f"reviewer1_{field}", "")
        right = row.get(f"reviewer2_{field}", "")
        if left == right:
            resolved = left
        elif "no" in {left, right}:
            resolved = "no"
        else:
            resolved = "unclear"
        row[f"resolved_{field}"] = resolved
        if left != right:
            notes.append(f"{field}: reviewer1={left}, reviewer2={right}")
    row["resolution_notes"] = "; ".join(notes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default="minimax-m2.7")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=0)
    args = parser.parse_args()

    rows = read_csv(args.input)
    fieldnames = list(rows[0].keys()) if rows else []
    reviewer_agents = {
        "reviewer1": build_agent(args.model, "reviewer1"),
        "reviewer2": build_agent(args.model, "reviewer2"),
    }

    processed = 0
    for row in rows:
        if args.limit and processed >= args.limit:
            break
        prompt = make_prompt(row)
        for reviewer, agent in reviewer_agents.items():
            if row.get(f"{reviewer}_subject_correct"):
                continue
            decision = agent.run_sync(
                prompt,
                model_settings={"temperature": args.temperature},
            ).output
            apply_decision(row, reviewer, decision)
            print(
                f"{row.get('audit_id')} {reviewer} "
                f"dir={decision.direction_correct} snippet={decision.snippet_supports_claim}",
                flush=True,
            )
        resolve(row)
        processed += 1
        write_csv(args.output, rows, fieldnames)

    write_csv(args.output, rows, fieldnames)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
