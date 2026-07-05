#!/usr/bin/env python3
"""Expand the selected Food-AI PubMed corpus with high-precision queries."""

import argparse
import json
import shutil
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "skills" / "pubmed" / "scripts"))

import pubmed_search  # type: ignore
from scripts.evaluation.score_papers import score_article


TODAY = "2026-04-25"


SEARCH_PLAN = [
    {
        "label": "core_fermented_dairy_rct_title",
        "query": '((yogurt[Title] OR yoghurt[Title] OR kefir[Title] OR "fermented milk"[Title] OR "fermented dairy"[Title]) AND Randomized Controlled Trial[Publication Type])',
        "max_pages": 8,
    },
    {
        "label": "core_fermented_dairy_clinical_title",
        "query": '((yogurt[Title] OR yoghurt[Title] OR kefir[Title] OR "fermented milk"[Title] OR "fermented dairy"[Title]) AND (Clinical Trial[Publication Type] OR controlled[Title/Abstract] OR placebo[Title/Abstract] OR crossover[Title/Abstract]))',
        "max_pages": 6,
    },
    {
        "label": "metabolic_fermented_dairy_rct",
        "query": '((yogurt[Title/Abstract] OR yoghurt[Title/Abstract] OR kefir[Title/Abstract] OR "fermented milk"[Title/Abstract] OR "fermented dairy"[Title/Abstract]) AND Randomized Controlled Trial[Publication Type] AND (diabetes[Title/Abstract] OR glycemic[Title/Abstract] OR glucose[Title/Abstract] OR cholesterol[Title/Abstract] OR lipid[Title/Abstract] OR triglyceride[Title/Abstract] OR "blood pressure"[Title/Abstract] OR hypertension[Title/Abstract] OR obesity[Title/Abstract] OR metabolic[Title/Abstract]))',
        "max_pages": 8,
    },
    {
        "label": "probiotic_clinical_metabolic",
        "query": '((probiotic[Title] OR probiotics[Title] OR synbiotic[Title] OR synbiotics[Title]) AND Randomized Controlled Trial[Publication Type] AND (diabetes[Title/Abstract] OR glycemic[Title/Abstract] OR glucose[Title/Abstract] OR cholesterol[Title/Abstract] OR lipid[Title/Abstract] OR triglyceride[Title/Abstract] OR "blood pressure"[Title/Abstract] OR obesity[Title/Abstract] OR metabolic[Title/Abstract] OR inflammation[Title/Abstract]))',
        "max_pages": 8,
    },
    {
        "label": "probiotic_gut_immune_rct",
        "query": '((probiotic[Title] OR probiotics[Title] OR synbiotic[Title] OR synbiotics[Title] OR postbiotic[Title] OR postbiotics[Title]) AND Randomized Controlled Trial[Publication Type] AND (microbiota[Title/Abstract] OR microbiome[Title/Abstract] OR gastrointestinal[Title/Abstract] OR gut[Title/Abstract] OR diarrhea[Title/Abstract] OR constipation[Title/Abstract] OR immune[Title/Abstract] OR inflammation[Title/Abstract]))',
        "max_pages": 8,
    },
    {
        "label": "fermented_food_microbiome_human",
        "query": '(("fermented food"[Title/Abstract] OR "fermented foods"[Title/Abstract] OR yogurt[Title/Abstract] OR yoghurt[Title/Abstract] OR kefir[Title/Abstract] OR kimchi[Title/Abstract] OR kombucha[Title/Abstract]) AND (microbiota[Title/Abstract] OR microbiome[Title/Abstract] OR gut[Title/Abstract]) AND (human[Title/Abstract] OR adults[Title/Abstract] OR patients[Title/Abstract] OR trial[Title/Abstract] OR intervention[Title/Abstract]))',
        "max_pages": 6,
    },
    {
        "label": "non_dairy_fermented_food_human",
        "query": '((kimchi[Title] OR kombucha[Title] OR natto[Title] OR miso[Title] OR tempeh[Title] OR sauerkraut[Title]) AND (human[Title/Abstract] OR adults[Title/Abstract] OR patients[Title/Abstract] OR trial[Title/Abstract] OR intervention[Title/Abstract] OR consumption[Title/Abstract]))',
        "max_pages": 5,
    },
    {
        "label": "fermented_food_reviews",
        "query": '((yogurt[Title] OR yoghurt[Title] OR kefir[Title] OR "fermented food"[Title] OR "fermented foods"[Title] OR kimchi[Title] OR kombucha[Title] OR natto[Title] OR miso[Title] OR tempeh[Title]) AND (systematic review[Title/Abstract] OR meta-analysis[Title/Abstract] OR review[Publication Type]))',
        "max_pages": 6,
    },
    {
        "label": "probiotic_health_reviews",
        "query": '((probiotic[Title] OR probiotics[Title] OR synbiotic[Title] OR synbiotics[Title] OR postbiotic[Title] OR postbiotics[Title]) AND (systematic review[Title/Abstract] OR meta-analysis[Title/Abstract]) AND (health[Title/Abstract] OR disease[Title/Abstract] OR microbiota[Title/Abstract] OR metabolic[Title/Abstract] OR immune[Title/Abstract] OR gastrointestinal[Title/Abstract]))',
        "max_pages": 6,
    },
]


DOMAIN_TERMS = [
    "yogurt",
    "yoghurt",
    "kefir",
    "fermented milk",
    "fermented dairy",
    "fermented food",
    "fermented foods",
    "kimchi",
    "kombucha",
    "natto",
    "miso",
    "tempeh",
    "sauerkraut",
    "probiotic",
    "probiotics",
    "synbiotic",
    "synbiotics",
    "postbiotic",
    "postbiotics",
]

OUTCOME_TERMS = [
    "diabetes",
    "glycemic",
    "glucose",
    "insulin",
    "cholesterol",
    "lipid",
    "triglyceride",
    "blood pressure",
    "hypertension",
    "obesity",
    "overweight",
    "metabolic",
    "inflammation",
    "microbiota",
    "microbiome",
    "gastrointestinal",
    "immune",
]

EXCLUDE_TERMS = [
    "fish",
    "shrimp",
    "broiler",
    "poultry",
    "piglet",
    "mouse model",
    "mice",
    "rat model",
    "in vitro",
    "bibliometric",
    "patent",
]


def text_values(items: list[Any]) -> list[str]:
    values = []
    for item in items or []:
        if isinstance(item, str):
            values.append(item)
        elif isinstance(item, dict):
            for key in ("name", "descriptor", "title", "text"):
                if item.get(key):
                    values.append(str(item[key]))
                    break
    return values


def pub_type_names(article: dict[str, Any]) -> list[str]:
    return text_values(article.get("publication_types", []))


def is_review(article: dict[str, Any]) -> bool:
    text = " ".join(pub_type_names(article)).lower() + " " + article.get("title", "").lower()
    return "review" in text or "meta-analysis" in text or "systematic review" in text


def is_rct_or_trial(article: dict[str, Any], study_type: str) -> bool:
    text = " ".join(pub_type_names(article)).lower() + " " + article.get("title", "").lower() + " " + article.get("abstract", "").lower()
    return (
        study_type in {"RCT", "Crossover trial"}
        or "randomized controlled trial" in text
        or "clinical trial" in text
        or "randomized" in text
        or "randomised" in text
        or "crossover" in text
    )


def article_text(article: dict[str, Any]) -> str:
    mesh = " ".join(text_values(article.get("mesh_terms", [])))
    return f"{article.get('title', '')} {article.get('abstract', '')} {mesh}".lower()


def expansion_score(article: dict[str, Any], base_score: dict[str, Any]) -> tuple[float, list[str]]:
    text = article_text(article)
    title = article.get("title", "").lower()
    reasons = []

    domain_hits = [term for term in DOMAIN_TERMS if term in text]
    title_domain_hits = [term for term in DOMAIN_TERMS if term in title]
    outcome_hits = [term for term in OUTCOME_TERMS if term in text]
    excluded = [term for term in EXCLUDE_TERMS if term in text]

    review = is_review(article)
    trial = is_rct_or_trial(article, base_score["study_type"])
    has_pmcid = bool(article.get("pmcid"))
    has_abstract = bool(article.get("abstract"))

    score = float(base_score["overall_quality"])
    score += min(len(set(domain_hits)), 5) * 3
    score += min(len(set(title_domain_hits)), 3) * 5
    score += min(len(set(outcome_hits)), 5) * 2

    if trial:
        score += 18
        reasons.append("clinical_trial_or_rct")
    if review:
        score += 6
        reasons.append("review")
    if review and has_pmcid:
        score += 8
        reasons.append("review_with_pmc_fulltext")
    if has_pmcid and not review:
        score += 3
        reasons.append("has_pmcid")
    if has_abstract:
        score += 2
    if title_domain_hits:
        reasons.append("domain_term_in_title")
    if outcome_hits:
        reasons.append("health_outcome_terms")
    if excluded:
        score -= 25
        reasons.append("excluded_context:" + ",".join(sorted(set(excluded))[:3]))
    if not domain_hits:
        score -= 50
        reasons.append("no_domain_term")
    if review and not has_pmcid:
        score -= 8
        reasons.append("review_abstract_only")

    return round(score, 2), reasons


def fetch_candidates(page_size: int, sleep_seconds: float, max_pages_per_query: int | None = None) -> dict[str, dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for spec in SEARCH_PLAN:
        pages = spec["max_pages"]
        if max_pages_per_query is not None:
            pages = min(pages, max_pages_per_query)
        for page in range(pages):
            start = page * page_size
            result = pubmed_search.search_pubmed(
                spec["query"],
                max_results=page_size,
                start_index=start,
                sort_order="relevance",
            )
            articles = result.get("articles", [])
            print(
                f"{spec['label']} page={page + 1}/{pages} "
                f"count={result.get('count')} returned={len(articles)}",
                flush=True,
            )
            for article in articles:
                pmid = article.get("pmid")
                if not pmid:
                    continue
                if pmid not in seen:
                    seen[pmid] = {"article": article, "source_queries": []}
                seen[pmid]["source_queries"].append(spec["label"])
            if not articles or len(articles) < page_size:
                break
            time.sleep(sleep_seconds)
    return seen


def selected_article_row(article: dict[str, Any], scored: dict[str, Any], source: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    row = {
        "pmid": article.get("pmid") or scored.get("pmid"),
        "title": article.get("title") or scored.get("title"),
        "journal": article.get("journal", "Unknown"),
        "year": article.get("pub_date") or article.get("year") or "Unknown",
        "study_type": scored.get("study_type", "Other/Unknown"),
        "quality_score": scored.get("overall_quality", scored.get("quality_score", 0)),
        "relevance_score": scored.get("relevance_score", 0),
        "source": source,
    }
    if extra:
        row.update(extra)
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Expand Food-AI selected PubMed corpus")
    parser.add_argument("--selected", type=Path, default=Path("data/processed/selected_141_quality.json"))
    parser.add_argument("--target-total", type=int, default=300)
    parser.add_argument("--page-size", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--max-pages-per-query", type=int, default=None)
    parser.add_argument("--out-dir", type=Path, default=Path("data/candidate_pool"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()

    selected_data = json.loads(args.selected.read_text())
    selected_articles = selected_data.get("articles", [])
    existing_pmids = {str(article["pmid"]) for article in selected_articles if article.get("pmid")}

    snapshot = args.processed_dir / f"selected_141_quality_snapshot_{TODAY}.json"
    if not snapshot.exists():
        shutil.copy2(args.selected, snapshot)

    fetched = fetch_candidates(args.page_size, args.sleep, args.max_pages_per_query)
    candidates = []
    for pmid, payload in fetched.items():
        if pmid in existing_pmids:
            continue
        article = payload["article"]
        base = score_article(article, has_xml=bool(article.get("pmcid"))).to_dict()
        score, reasons = expansion_score(article, base)
        candidate = {
            **base,
            "expansion_score": score,
            "selection_reasons": reasons,
            "source_queries": sorted(set(payload["source_queries"])),
            "journal": article.get("journal", ""),
            "pub_date": article.get("pub_date", ""),
            "doi": article.get("doi"),
            "pmcid": article.get("pmcid"),
            "has_pmcid": bool(article.get("pmcid")),
            "is_review": is_review(article),
            "is_trial": is_rct_or_trial(article, base["study_type"]),
            "publication_types": article.get("publication_types", []),
            "abstract": article.get("abstract", ""),
        }
        candidates.append(candidate)

    candidates.sort(key=lambda item: (item["expansion_score"], item["overall_quality"], item["relevance_score"]), reverse=True)

    needed = max(0, args.target_total - len(selected_articles))
    proposed_new = candidates[:needed]

    proposed_articles = []
    for article in selected_articles:
        proposed_articles.append({**article, "source": article.get("source", "selected_141")})
    for candidate in proposed_new:
        extra = {
            "expansion_score": candidate["expansion_score"],
            "selection_reasons": candidate["selection_reasons"],
            "source_queries": candidate["source_queries"],
            "has_pmcid": candidate["has_pmcid"],
            "is_review": candidate["is_review"],
            "is_trial": candidate["is_trial"],
        }
        proposed_articles.append(selected_article_row(candidate, candidate, "pubmed_expansion_20260425", extra))

    study_counter = Counter(article.get("study_type", "Unknown") for article in proposed_articles)
    review_count = sum(1 for article in proposed_articles if article.get("is_review") or article.get("study_type") == "Meta-analysis/Review")
    trial_count = sum(1 for article in proposed_articles if article.get("is_trial") or article.get("study_type") in {"RCT", "Crossover trial"})

    raw_path = args.out_dir / f"pubmed_expansion_candidates_{TODAY}.json"
    selected_path = args.processed_dir / f"selected_{len(proposed_articles)}_quality_proposed_{TODAY}.json"
    audit_path = args.out_dir / f"pubmed_expansion_audit_{TODAY}.json"

    raw_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now().isoformat(),
                "search_plan": SEARCH_PLAN,
                "existing_count": len(selected_articles),
                "target_total": args.target_total,
                "candidate_count": len(candidates),
                "candidates": candidates,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    selected_path.write_text(
        json.dumps(
            {
                "total": len(proposed_articles),
                "previous_total": len(selected_articles),
                "new_count": len(proposed_new),
                "primary_count": trial_count,
                "review_count": review_count,
                "selection_criteria": {
                    "base": str(args.selected),
                    "snapshot": str(snapshot),
                    "target_total": args.target_total,
                    "method": "strict PubMed query expansion with scoring; proposed list for manual confirmation",
                },
                "articles": proposed_articles,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    audit_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now().isoformat(),
                "snapshot": str(snapshot),
                "raw_candidates": str(raw_path),
                "proposed_selected": str(selected_path),
                "candidate_count": len(candidates),
                "new_selected_count": len(proposed_new),
                "final_total": len(proposed_articles),
                "study_type_counts": dict(study_counter),
                "trial_count": trial_count,
                "review_count": review_count,
                "new_review_with_pmcid": sum(1 for item in proposed_new if item["is_review"] and item["has_pmcid"]),
                "new_review_abstract_only": sum(1 for item in proposed_new if item["is_review"] and not item["has_pmcid"]),
                "top_new_pmids": [item["pmid"] for item in proposed_new[:25]],
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    print(f"snapshot={snapshot}", flush=True)
    print(f"raw_candidates={raw_path}", flush=True)
    print(f"proposed_selected={selected_path}", flush=True)
    print(f"audit={audit_path}", flush=True)
    print(f"candidate_count={len(candidates)} new_selected={len(proposed_new)} final_total={len(proposed_articles)}", flush=True)
    print(f"trial_count={trial_count} review_count={review_count}", flush=True)
    print("top_new:", flush=True)
    for item in proposed_new[:20]:
        print(item["pmid"], item["expansion_score"], item["study_type"], item["title"][:100], flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
