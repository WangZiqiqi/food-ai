#!/usr/bin/env python3
"""
translated note - translated note PubMed translated note
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class QualityScores:
    """translated note"""
    pmid: str
    title: str
    
    # translated note (1-5)
    relevance_score: float  # 1-5
    relevance_reasoning: str
    
    # translated note (0-100)
    study_design_score: float
    outcome_clarity_score: float
    sample_size_score: float
    full_text_score: float
    
    # translated note
    overall_quality: float  # 0-100
    
    # translated note
    study_type: str
    sample_size: Optional[int]
    has_full_text: bool
    
    def to_dict(self) -> Dict:
        return asdict(self)


def _text_values(items: List) -> List[str]:
    """Normalize PubMed metadata fields that may be strings or dict objects."""
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


def score_study_design(article: Dict) -> tuple[float, str]:
    """translated note"""
    pub_types = _text_values(article.get("publication_types", []))
    title = article.get("title", "").lower()
    abstract = article.get("abstract", "").lower()
    
    # translated note RCT
    is_rct = any(pt in pub_types for pt in ["Randomized Controlled Trial", "Clinical Trial"])
    is_rct = is_rct or "randomized" in title or "randomised" in title
    is_rct = is_rct or "double-blind" in abstract or "placebo-controlled" in abstract
    
    # translated note crossover
    is_crossover = "crossover" in title or "cross-over" in title
    
    # translated note Meta-analysis
    is_meta = any(pt in pub_types for pt in ["Meta-Analysis", "Review", "Systematic Review"])
    is_meta = is_meta or "meta-analysis" in title or "systematic review" in title
    
    if is_rct:
        return 100.0, "RCT"
    elif is_crossover:
        return 90.0, "Crossover trial"
    elif "Cohort" in pub_types:
        return 70.0, "Cohort study"
    elif "Case-Control" in pub_types:
        return 50.0, "Case-control study"
    elif is_meta:
        return 30.0, "Meta-analysis/Review"
    else:
        return 40.0, "Other/Unknown"


def score_outcome_clarity(article: Dict) -> tuple[float, str]:
    """translated note"""
    abstract = article.get("abstract", "")
    title = article.get("title", "")
    
    # translated note
    metabolic_outcomes = [
        "hba1c", "glycemic", "glucose", "insulin", "diabetes",
        "cholesterol", "ldl", "hdl", "triglyceride", "lipid",
        "weight", "bmi", "obesity", "body mass",
        "blood pressure", "hypertension"
    ]
    
    gut_outcomes = ["microbiome", "microbiota", "gut", "probiotic"]
    
    has_metabolic = any(term in abstract.lower() or term in title.lower() 
                        for term in metabolic_outcomes)
    has_gut = any(term in abstract.lower() or term in title.lower() 
                  for term in gut_outcomes)
    
    # translated note
    has_numbers = any(char.isdigit() for char in abstract)
    
    if has_metabolic and has_numbers:
        return 100.0, "Clear metabolic outcomes with data"
    elif has_metabolic:
        return 80.0, "Metabolic outcomes mentioned"
    elif has_gut and has_numbers:
        return 75.0, "Gut health outcomes with data"
    elif has_gut:
        return 60.0, "Gut health mentioned"
    else:
        return 40.0, "Outcomes unclear or not metabolic/gut related"


def score_sample_size(article: Dict) -> tuple[float, Optional[int]]:
    """translated note"""
    abstract = article.get("abstract", "")
    
    # translated note
    import re
    
    # translated note
    patterns = [
        r'(\d+)\s*(?:participants|subjects|patients|individuals|volunteers)',
        r'n\s*=\s*(\d+)',
        r'(?:enrolled|recruited|included)\s+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, abstract.lower())
        if match:
            n = int(match.group(1))
            if n >= 100:
                return 100.0, n
            elif n >= 50:
                return 80.0, n
            elif n >= 20:
                return 60.0, n
            else:
                return 40.0, n
    
    return 50.0, None  # translated note


def score_relevance(article: Dict) -> tuple[float, str]:
    """translated note"""
    title = article.get("title", "").lower()
    abstract = article.get("abstract", "").lower()
    mesh_terms = [t.lower() for t in _text_values(article.get("mesh_terms", []))]
    keywords = [k.lower() for k in _text_values(article.get("keywords", []))]
    
    # translated note
    fermented_foods = [
        "yogurt", "yoghurt", "kefir", "kimchi", "kombucha",
        "sauerkraut", "miso", "tempeh", "natto", "fermented",
        "probiotic", "lactobacillus", "bifidobacterium"
    ]
    
    # translated note
    text_to_check = title + " " + abstract + " " + " ".join(mesh_terms + keywords)
    
    matches = [food for food in fermented_foods if food in text_to_check]
    
    # translated note RCT
    is_rct = "randomized" in text_to_check or "clinical trial" in text_to_check
    
    # translated note
    if len(matches) >= 2 and is_rct:
        return 5.0, f"High relevance: {', '.join(matches[:3])}, RCT"
    elif len(matches) >= 1 and is_rct:
        return 4.0, f"Good relevance: {', '.join(matches[:2])}, RCT"
    elif len(matches) >= 2:
        return 3.0, f"Moderate relevance: {', '.join(matches[:2])}, non-RCT"
    elif len(matches) >= 1:
        return 2.0, f"Low relevance: {matches[0]}"
    else:
        return 1.0, "Not relevant to fermented foods"


def calculate_overall_quality(scores: Dict) -> float:
    """translated note"""
    weights = {
        "study_design": 0.4,
        "outcome_clarity": 0.3,
        "sample_size": 0.2,
        "full_text": 0.1
    }
    
    overall = (
        scores["study_design"] * weights["study_design"] +
        scores["outcome_clarity"] * weights["outcome_clarity"] +
        scores["sample_size"] * weights["sample_size"] +
        scores["full_text"] * weights["full_text"]
    )
    
    return round(overall, 2)


def score_article(article: Dict, has_xml: bool = False) -> QualityScores:
    """translated note"""
    pmid = article.get("pmid", "unknown")
    title = article.get("title", "")
    
    # translated note
    study_design_score, study_type = score_study_design(article)
    outcome_clarity_score, _ = score_outcome_clarity(article)
    sample_size_score, sample_size = score_sample_size(article)
    relevance_score, relevance_reasoning = score_relevance(article)
    
    full_text_score = 100.0 if has_xml else 0.0
    
    # translated note
    quality_scores = {
        "study_design": study_design_score,
        "outcome_clarity": outcome_clarity_score,
        "sample_size": sample_size_score,
        "full_text": full_text_score
    }
    overall_quality = calculate_overall_quality(quality_scores)
    
    return QualityScores(
        pmid=pmid,
        title=title,
        relevance_score=relevance_score,
        relevance_reasoning=relevance_reasoning,
        study_design_score=study_design_score,
        outcome_clarity_score=outcome_clarity_score,
        sample_size_score=sample_size_score,
        full_text_score=full_text_score,
        overall_quality=overall_quality,
        study_type=study_type,
        sample_size=sample_size,
        has_full_text=has_xml
    )


def batch_score_articles(articles_file: Path, xml_dir: Optional[Path] = None) -> List[QualityScores]:
    """translated note"""
    # translated note
    with open(articles_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    articles = data.get("articles", [])
    print(f"translated note {len(articles)} translated note")
    
    # translated note XML translated note PMID translated note
    has_xml_pmids = set()
    if xml_dir and xml_dir.exists():
        has_xml_pmids = {f.stem for f in xml_dir.glob("*.xml")}
        print(f"translated note {len(has_xml_pmids)} translated note XML translated note")
    
    # translated note
    results = []
    for i, article in enumerate(articles, 1):
        pmid = article.get("pmid", "unknown")
        has_xml = pmid in has_xml_pmids
        
        score = score_article(article, has_xml)
        results.append(score)
        
        if i % 50 == 0:
            print(f"  translated note {i}/{len(articles)} translated note...")
    
    return results


def save_results(results: List[QualityScores], output_file: Path):
    """translated note"""
    output_data = {
        "total_articles": len(results),
        "scored_at": "2026-02-28T20:30:00Z",
        "scoring_method": "rule_based",
        "summary": {
            "avg_relevance": round(sum(r.relevance_score for r in results) / len(results), 2),
            "avg_quality": round(sum(r.overall_quality for r in results) / len(results), 2),
            "high_quality_count": sum(1 for r in results if r.overall_quality >= 70),
            "with_xml_count": sum(1 for r in results if r.has_full_text),
        },
        "scores": [r.to_dict() for r in results]
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\ntranslated note: {output_file}")
    print(f"translated note:")
    print(f"  translated note: {output_data['summary']['avg_relevance']}/5")
    print(f"  translated note: {output_data['summary']['avg_quality']}/100")
    print(f"  translated note(≥70): {output_data['summary']['high_quality_count']}")
    print(f"  translated note XML: {output_data['summary']['with_xml_count']}")


def main():
    parser = argparse.ArgumentParser(description="translated note")
    parser.add_argument("--input", type=Path, default=Path("data/metadata/all_articles.json"),
                        help="translated note")
    parser.add_argument("--xml-dir", type=Path, default=Path("data/xml"),
                        help="XML translated note")
    parser.add_argument("--output", type=Path, default=Path("data/quality_scores.json"),
                        help="translated note")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("translated note")
    print("=" * 60)
    
    # translated note
    results = batch_score_articles(args.input, args.xml_dir)
    
    # translated note
    save_results(results, args.output)
    
    print("\n translated note!")


if __name__ == "__main__":
    main()
