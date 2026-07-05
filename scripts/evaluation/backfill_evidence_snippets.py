#!/usr/bin/env python3
"""Backfill missing evidence snippets from stored PubMed abstracts.

This is a deterministic repair for existing extraction artifacts. It does not
call an LLM. For each evidence item with an empty `evidence_snippet`, it selects
the most relevant sentence from the source abstract using subject/outcome token
overlap and stored statistical fields when available.
"""

from __future__ import annotations

import argparse
import copy
import json
import pickle
import re
from collections import Counter
from pathlib import Path
from typing import Any

import networkx as nx
from networkx.readwrite import json_graph


DEFAULT_EXTRACTION = Path("data/processed/final_graph/food_ai_graph.json")
DEFAULT_GRAPH_PICKLE = Path("data/processed/final_graph/food_ai_graph.pkl")
DEFAULT_GRAPH_JSON = Path("data/processed/final_graph/food_ai_graph_networkx.json")
DEFAULT_ARTICLES = Path("data/processed/selected_850_quality_llm_abstract_complete_2026-04-26.json")
DEFAULT_REPORT_JSON = Path("data/evaluation/snippet_backfill_850_report.json")
DEFAULT_REPORT_MD = Path("data/evaluation/snippet_backfill_850_report.md")

STOPWORDS = {
    "and",
    "are",
    "effect",
    "effects",
    "for",
    "has",
    "have",
    "having",
    "into",
    "not",
    "of",
    "on",
    "the",
    "this",
    "to",
    "with",
}

METHOD_CUES = {
    "aim",
    "aimed",
    "aims",
    "determine",
    "determined",
    "evaluate",
    "evaluated",
    "investigate",
    "investigated",
    "objective",
    "objectives",
    "protocol",
    "purpose",
    "study",
}

RESULT_CUES = {
    "associated",
    "changed",
    "decrease",
    "decreased",
    "difference",
    "differences",
    "found",
    "greater",
    "improve",
    "improved",
    "increase",
    "increased",
    "less",
    "lower",
    "reduced",
    "result",
    "results",
    "significant",
    "significantly",
    "showed",
    "suggest",
    "suggested",
    "was",
    "were",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def article_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("articles", "results", "papers", "selected"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    raise ValueError("could not find article list")


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", text)
    return [part.strip() for part in parts if len(part.strip()) >= 25]


def tokens(text: str) -> set[str]:
    normalized = re.sub(r"[_\-/]+", " ", text.lower())
    found = re.findall(r"[a-z][a-z0-9]+", normalized)
    return {tok for tok in found if len(tok) >= 3 and tok not in STOPWORDS}


def direction_tokens(direction: str) -> set[str]:
    if direction == "positive":
        return {
            "beneficial",
            "decrease",
            "decreased",
            "decreases",
            "improve",
            "improved",
            "improves",
            "increase",
            "increased",
            "increases",
            "lower",
            "lowered",
            "reduce",
            "reduced",
            "reduces",
            "significant",
            "significantly",
        }
    if direction == "negative":
        return {
            "adverse",
            "decrease",
            "decreased",
            "harmful",
            "increase",
            "increased",
            "increases",
            "risk",
            "worse",
            "worsen",
            "worsened",
        }
    if direction == "neutral":
        return {
            "absence",
            "difference",
            "insignificant",
            "neutral",
            "none",
            "not",
            "significant",
            "significantly",
            "unchanged",
        }
    return set()


def score_sentence(sentence: str, claim: dict[str, Any], evidence: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    sentence_lower = sentence.lower()
    sentence_tokens = tokens(sentence)
    subject_tokens = tokens(claim.get("subject_name", ""))
    object_tokens = tokens(claim.get("object_name", ""))
    claim_tokens = tokens(claim.get("claim_text", ""))
    direction = claim.get("direction", "")

    subject_hits = sentence_tokens & subject_tokens
    object_hits = sentence_tokens & object_tokens
    claim_hits = sentence_tokens & claim_tokens
    direction_hits = sentence_tokens & direction_tokens(direction)

    score = 0.0
    score += 4.0 * len(subject_hits)
    score += 5.0 * len(object_hits)
    score += 1.0 * len(claim_hits)
    score += 0.5 * min(len(direction_hits), 2)

    method_hits = sentence_tokens & METHOD_CUES
    result_hits = sentence_tokens & RESULT_CUES
    method_phrase = bool(
        re.search(
            r"\b(aim|aimed|objective|objectives|purpose)\b|"
            r"\b(study|trial)\s+(was\s+)?(designed|conducted)\s+to\b|"
            r"\b(to|we)\s+(determine|evaluate|investigate)\b|"
            r"\bwas\s+performed\b",
            sentence_lower,
        )
    )
    if method_phrase:
        score -= 25.0
    elif method_hits and not result_hits:
        score -= 12.0
    elif method_hits:
        score -= 4.0

    if result_hits:
        score += min(len(result_hits), 3)

    for field in ("effect_size", "p_value", "confidence_interval"):
        value = evidence.get(field)
        if value and str(value).lower() in sentence_lower:
            score += 4.0

    # Abstracts often use singular/plural or broader terms. Give a small
    # fallback boost when the sentence mentions common food/intervention words.
    if subject_tokens and not subject_hits:
        broad_subject_terms = {"food", "foods", "fermented", "probiotic", "probiotics", "yogurt", "kefir"}
        if sentence_tokens & broad_subject_terms:
            score += 1.0

    detail = {
        "subject_hits": sorted(subject_hits),
        "object_hits": sorted(object_hits),
        "claim_hits": sorted(claim_hits),
        "direction_hits": sorted(direction_hits),
        "method_hits": sorted(method_hits),
        "method_phrase": method_phrase,
        "result_hits": sorted(result_hits),
    }
    return score, detail


def best_snippet(
    abstract: str,
    claim: dict[str, Any],
    evidence: dict[str, Any],
    min_score: float,
) -> tuple[str, float, dict[str, Any]]:
    candidates = []
    for sentence in split_sentences(abstract):
        score, detail = score_sentence(sentence, claim, evidence)
        candidates.append((score, sentence, detail))
    if not candidates:
        return "", 0.0, {}
    score, sentence, detail = max(candidates, key=lambda item: item[0])
    if score < min_score:
        return "", score, detail
    return sentence, score, detail


def evidence_stats(claims: list[dict[str, Any]]) -> dict[str, int]:
    total = 0
    empty = 0
    backfilled = 0
    for claim in claims:
        for evidence in claim.get("evidence_list") or []:
            total += 1
            if not (evidence.get("evidence_snippet") or "").strip():
                empty += 1
            if evidence.get("evidence_snippet_source") == "abstract_sentence_backfill":
                backfilled += 1
    return {"total": total, "empty": empty, "nonempty": total - empty, "backfilled": backfilled}


def update_networkx_artifacts(
    graph_pickle: Path,
    graph_json: Path,
    claims_by_id: dict[str, dict[str, Any]],
    dry_run: bool,
) -> bool:
    if not graph_pickle.exists():
        return False
    with graph_pickle.open("rb") as f:
        graph = pickle.load(f)
    if not isinstance(graph, nx.Graph):
        raise TypeError(f"{graph_pickle} did not contain a NetworkX graph")

    changed = False
    for claim_id, claim in claims_by_id.items():
        if claim_id in graph.nodes:
            graph.nodes[claim_id]["evidence_list"] = copy.deepcopy(claim.get("evidence_list", []))
            changed = True

    if changed and not dry_run:
        with graph_pickle.open("wb") as f:
            pickle.dump(graph, f)
        write_json(graph_json, json_graph.node_link_data(graph, edges="links"))
    return changed


def render_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Evidence Snippet Backfill Report",
        "",
        f"Extraction: `{report['extraction']}`",
        f"Articles: `{report['articles']}`",
        f"Minimum score: `{report['min_score']}`",
        "",
        "## Summary",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in summary.items():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Filled By Score Band", "| Score band | Count |", "| --- | ---: |"])
    for band, count in sorted(report["filled_score_bands"].items()):
        lines.append(f"| {band} | {count} |")
    lines.extend(["", "## Notes", ""])
    lines.append("- Only evidence items with empty `evidence_snippet` were modified.")
    lines.append("- Candidate snippets were selected from stored PubMed abstracts without LLM calls.")
    lines.append("- Low-scoring candidates were left empty to avoid adding weakly related snippets.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extraction", type=Path, default=DEFAULT_EXTRACTION)
    parser.add_argument("--articles", type=Path, default=DEFAULT_ARTICLES)
    parser.add_argument("--graph-pickle", type=Path, default=DEFAULT_GRAPH_PICKLE)
    parser.add_argument("--graph-json", type=Path, default=DEFAULT_GRAPH_JSON)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--min-score", type=float, default=12.0)
    parser.add_argument("--replace-backfilled", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    extraction = load_json(args.extraction)
    claims = extraction.get("merged_claims")
    if not isinstance(claims, list):
        raise ValueError("extraction JSON must contain merged_claims")

    articles = {
        str(article.get("pmid")): article
        for article in article_records(load_json(args.articles))
        if article.get("pmid") and article.get("abstract")
    }

    before = evidence_stats(claims)
    effective_empty_before = before["empty"] + before["backfilled"] if args.replace_backfilled else before["empty"]
    attempted = 0
    filled = 0
    no_abstract = 0
    low_score = 0
    score_bands: Counter[str] = Counter()
    examples = []

    for claim in claims:
        for evidence in claim.get("evidence_list") or []:
            is_backfilled = evidence.get("evidence_snippet_source") == "abstract_sentence_backfill"
            if (evidence.get("evidence_snippet") or "").strip() and not (
                args.replace_backfilled and is_backfilled
            ):
                continue
            attempted += 1
            pmid = str(evidence.get("pmid") or "")
            abstract = (articles.get(pmid) or {}).get("abstract", "")
            if not abstract:
                no_abstract += 1
                continue
            snippet, score, detail = best_snippet(abstract, claim, evidence, args.min_score)
            if not snippet:
                if args.replace_backfilled and is_backfilled:
                    evidence["evidence_snippet"] = ""
                    evidence.pop("evidence_snippet_source", None)
                    evidence.pop("evidence_snippet_score", None)
                    evidence.pop("evidence_snippet_match", None)
                low_score += 1
                continue

            evidence["evidence_snippet"] = snippet
            evidence["evidence_snippet_source"] = "abstract_sentence_backfill"
            evidence["evidence_snippet_score"] = round(score, 3)
            evidence["evidence_snippet_match"] = detail
            filled += 1
            band = f"{int(score // 5 * 5)}-{int(score // 5 * 5 + 4)}"
            score_bands[band] += 1
            if len(examples) < 10:
                examples.append(
                    {
                        "claim_id": claim.get("claim_id"),
                        "claim_text": claim.get("claim_text"),
                        "pmid": pmid,
                        "score": round(score, 3),
                        "snippet": snippet,
                    }
                )

    after = evidence_stats(claims)
    claims_by_id = {claim["claim_id"]: claim for claim in claims if claim.get("claim_id")}
    graph_updated = update_networkx_artifacts(args.graph_pickle, args.graph_json, claims_by_id, args.dry_run)

    report = {
        "extraction": str(args.extraction),
        "articles": str(args.articles),
        "min_score": args.min_score,
        "dry_run": args.dry_run,
        "summary": {
            "claims": len(claims),
            "evidence_total": before["total"],
            "stored_empty_before": before["empty"],
            "existing_backfilled_before": before["backfilled"],
            "effective_empty_before": effective_empty_before,
            "pre_backfill_nonempty_estimate": before["total"] - effective_empty_before,
            "nonempty_before": before["nonempty"],
            "attempted": attempted,
            "filled": filled,
            "no_abstract": no_abstract,
            "low_score_unfilled": low_score,
            "empty_after": after["empty"],
            "nonempty_after": after["nonempty"],
            "nonempty_rate_before": round(before["nonempty"] / before["total"], 4) if before["total"] else 0,
            "pre_backfill_nonempty_rate_estimate": round(
                (before["total"] - effective_empty_before) / before["total"], 4
            )
            if before["total"]
            else 0,
            "nonempty_rate_after": round(after["nonempty"] / after["total"], 4) if after["total"] else 0,
            "graph_artifacts_updated": graph_updated and not args.dry_run,
        },
        "filled_score_bands": dict(score_bands),
        "examples": examples,
    }

    if not args.dry_run:
        write_json(args.extraction, extraction)
        write_json(args.report_json, report)
        args.report_md.write_text(render_report(report), encoding="utf-8")

    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
