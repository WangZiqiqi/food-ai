"""
Deterministic helpers for narrowing review output into typed refine candidates.
"""

from __future__ import annotations

import re
from typing import Any


SUPPORTED_ACTIONS = {
    "merge",
    "rename",
    "normalize",
    "delete",
    "delete_orphan",
    "retype",
    "update_type",
    "set_name",
    "mark_out_of_scope",
    "preserve",
    "no_change",
    "skip",
}

ACTION_PRIORITY = {
    "merge": 0,
    "rename": 1,
    "normalize": 2,
    "update_type": 3,
    "retype": 3,
    "delete_orphan": 4,
    "set_name": 5,
    "mark_out_of_scope": 6,
    "delete": 7,
    "preserve": 8,
    "no_change": 9,
    "skip": 10,
}

SEVERITY_PRIORITY = {
    "critical": 0,
    "major": 1,
    "minor": 2,
    "unknown": 3,
}


def extract_refine_candidates_from_review(review_raw: str) -> list[dict[str, Any]]:
    sections = re.split(r"(?m)^###\s+", review_raw)
    candidates: list[dict[str, Any]] = []

    for section in sections:
        section = section.strip()
        if not section.startswith("ISSUE-"):
            continue

        lines = section.splitlines()
        header = lines[0].strip()
        issue_id, issue_type, header_entity = _parse_header(header)
        fields = _parse_fields(lines[1:])

        entity_value = fields.get("Entity", header_entity)
        entity_name, entity_type = _parse_entity(entity_value)
        raw_suggested_action = fields.get("Suggested Action", "skip")
        suggested_action = _normalize_action(raw_suggested_action)
        pmids = _parse_pmids(fields.get("PMIDs Affected", ""))

        candidates.append(
            {
                "issue_id": issue_id,
                "issue_type": issue_type,
                "entity_name": entity_name,
                "entity_type": entity_type,
                "severity": fields.get("Severity", "unknown").lower(),
                "suggested_action": suggested_action,
                "raw_suggested_action": raw_suggested_action,
                "confidence": fields.get("Confidence", "unknown").lower(),
                "current_state": fields.get("Current State", ""),
                "expected_state": fields.get("Expected State", ""),
                "evidence": fields.get("Evidence", ""),
                "pmids_affected": pmids,
                "source": "review_report",
            }
        )

    return candidates


NOOP_ACTIONS = {"preserve", "no_change", "skip"}


def select_refine_candidates(candidates: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    actionable = [
        candidate for candidate in candidates
        if candidate.get("suggested_action") in SUPPORTED_ACTIONS
        and candidate.get("suggested_action") not in NOOP_ACTIONS
    ]
    actionable.sort(
        key=lambda candidate: (
            SEVERITY_PRIORITY.get(candidate.get("severity", "unknown"), 99),
            ACTION_PRIORITY.get(candidate.get("suggested_action", "skip"), 99),
            candidate.get("issue_id", ""),
        )
    )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for candidate in actionable:
        key = (
            candidate.get("issue_id", ""),
            candidate.get("entity_name", ""),
            candidate.get("suggested_action", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)

    return deduped[:limit]


def _parse_header(header: str) -> tuple[str, str, str]:
    match = re.match(r"(ISSUE-\d+):\s*\[?([^\]]+)\]?\s*-\s*(.+)", header)
    if not match:
        issue_id = header.split(":")[0].strip()
        return issue_id, "unknown", ""
    return match.group(1).strip(), match.group(2).strip().lower(), match.group(3).strip()


def _parse_fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        match = re.match(r"-\s+\*\*(.+?)\*\*:\s*(.*)", stripped)
        if match:
            fields[match.group(1).strip()] = match.group(2).strip()
    return fields


def _parse_entity(value: str) -> tuple[str, str]:
    # translated note "name (type)",translated note "kefir (food) -> c-reactive_protein (outcome)"
    # translated note entity_type.
    match = re.match(r"([^(]+?)\s*\(([^()]+?)\)", value)
    if match:
        return match.group(1).strip(), match.group(2).strip().lower()
    return value.strip(), "unknown"


def _normalize_action(value: str) -> str:
    action = value.strip().lower()
    action = action.replace("-", "_").replace(" ", "_")
    if "manual_review" in action:
        return "preserve"
    if action in {"no_op", "noop"}:
        return "no_change"
    if "update_type" in action or "retype" in action or "change_type" in action:
        return "retype"
    if "delete_orphan" in action or "remove_orphan" in action:
        return "delete_orphan"
    if "out_of_scope" in action or "domain_drift" in action:
        return "mark_out_of_scope"
    if "set_name" in action or "display_name" in action or "title_case" in action:
        return "set_name"
    if action.startswith("delete") or action.startswith("remove"):
        return "delete"
    if action.startswith("merge"):
        return "merge"
    if action.startswith("rename"):
        return "rename"
    if action.startswith("normalize"):
        return "normalize"
    if action.startswith("preserve"):
        return "preserve"
    if action.startswith("no_change"):
        return "no_change"
    return action if action in SUPPORTED_ACTIONS else "skip"


def _parse_pmids(value: str) -> list[str]:
    return [pmid.strip() for pmid in value.split(",") if pmid.strip()]
