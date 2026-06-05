#!/usr/bin/env python3
"""
translated note
translated note LLM translated note

translated note:
    python scripts/filter_relevance.py --input data/metadata/all_articles.json --output data/metadata/relevant_articles.json --topic "translated note"
    
    # translated note
    python scripts/filter_relevance.py --input data/metadata/all_articles.json --topic "translated note" --prompt "translated note, translated note, translated note"
    
    # translated note
    python scripts/filter_relevance.py --input data/metadata/all_articles.json --batch-size 50 --save-interval 10
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Literal, Optional
from dataclasses import dataclass
from datetime import datetime
from tqdm import tqdm

# translated note
sys.path.insert(0, str(Path(__file__).parent.parent))


try:
    from pydantic import BaseModel, Field
    from pydantic_ai import Agent
except ImportError:
    print("translated note: pip install pydantic-ai")
    sys.exit(1)

from food_ai.pydantic_ai_client import create_poe_model


# ==================== translated note ====================

DEFAULT_SYSTEM_PROMPT = """translated note.translated note,translated note.

translated note,translated note:
- RELEVANT: translated note
- PARTIALLY: translated note(translated note)
- NOT_RELEVANT: translated note

translated note JSON translated note,translated note:
- relevance: "RELEVANT" | "PARTIALLY" | "NOT_RELEVANT"
- confidence: 0-1 translated note
- reason: translated note(1-2translated note)

translated note JSON,translated note."""

DEFAULT_USER_PROMPT_TEMPLATE = """translated note: {topic}

translated note: {title}
translated note: {abstract}

translated note,translated note JSON translated note."""


class RelevanceJudgement(BaseModel):
    """Structured relevance decision returned by pydantic-ai."""
    relevance: Literal["RELEVANT", "PARTIALLY", "NOT_RELEVANT"] = Field(description="translated note")
    confidence: float = Field(ge=0.0, le=1.0, description="0-1 translated note")
    reason: str = Field(description="translated note,1-2 translated note")


@dataclass
class RelevanceResult:
    """translated note"""
    pmid: str
    title: str
    relevance: str  # RELEVANT, PARTIALLY, NOT_RELEVANT
    confidence: float
    reason: str
    judged_at: str
    model: str


def get_relevance_agent(system_prompt: str | None = None, model: str = "minimax-m2.7") -> Agent:
    """translated note pydantic-ai translated note Agent."""
    return Agent(
        create_poe_model(model),
        output_type=RelevanceJudgement,
        system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
        retries=2,
    )


def judge_relevance(
    agent: Agent,
    title: str,
    abstract: str,
    topic: str,
    system_prompt: str = None,
    model: str = "minimax-m2.7",
    temperature: float = 0.1
) -> Optional[Dict]:
    """
    translated note LLM translated note
    
    Args:
        agent: pydantic-ai translated note Agent
        title: translated note
        abstract: translated note
        topic: translated note
        system_prompt: translated note
        model: translated note
        temperature: translated note
        
    Returns:
        translated note relevance, confidence, reason translated note,translated note None(translated note)
    """
    user_prompt = DEFAULT_USER_PROMPT_TEMPLATE.format(
        topic=topic,
        title=title,
        abstract=abstract[:2000] if abstract else "translated note"  # translated note
    )
    
    try:
        result = agent.run_sync(user_prompt, model_settings={"temperature": temperature}).output
        return {
            "relevance": result.relevance,
            "confidence": result.confidence,
            "reason": result.reason,
        }
        
    except Exception as e:
        print(f"  translated note: {e}")
        return None


def process_article(
    article: Dict,
    agent: Agent,
    topic: str,
    system_prompt: str = None,
    model: str = "minimax-m2.7",
    temperature: float = 0.1
) -> Optional[RelevanceResult]:
    """translated note"""
    pmid = article.get("pmid", "")
    title = article.get("title", "")
    abstract = article.get("abstract", "")
    
    if not title:
        return None
    
    result = judge_relevance(
        agent=agent,
        title=title,
        abstract=abstract,
        topic=topic,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature
    )
    
    if result:
        return RelevanceResult(
            pmid=pmid,
            title=title,
            relevance=result["relevance"],
            confidence=result["confidence"],
            reason=result["reason"],
            judged_at=datetime.now().isoformat(),
            model=model
        )
    
    return None


def filter_articles(
    input_file: Path,
    output_file: Path,
    topic: str,
    system_prompt: str = None,
    model: str = "minimax-m2.7",
    temperature: float = 0.1,
    batch_size: int = 100,
    save_interval: int = 10,
    min_confidence: float = 0.0,
    max_workers: int = 1,
    resume: bool = True
) -> Dict:
    """
    translated note
    
    Args:
        input_file: translated note all_articles.json translated note
        output_file: translated note
        topic: translated note
        system_prompt: translated note
        model: translated note
        temperature: translated note
        batch_size: translated note
        save_interval: translated note
        min_confidence: translated note(translated note UNCERTAIN)
        max_workers: translated note(translated note1,translated note API translated note)
        resume: translated note
        
    Returns:
        translated note
    """
    agent = get_relevance_agent(system_prompt=system_prompt, model=model)
    
    # translated note
    print(f"translated note: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    articles = data.get("articles", [])
    total = len(articles)
    print(f"translated note {total} translated note")
    
    # translated note(translated note resume=True)
    processed_pmids = set()
    results = []
    
    if resume and output_file.exists():
        print(f"translated note,translated note: {output_file}")
        with open(output_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            results = existing_data.get("results", [])
            processed_pmids = {r["pmid"] for r in results}
        print(f"translated note {len(results)} translated note,translated note {total - len(results)} translated note")
    
    # translated note
    articles_to_process = [a for a in articles if a["pmid"] not in processed_pmids]
    
    # translated note
    stats = {
        "total": total,
        "processed": len(results),
        "relevant": sum(1 for r in results if r["relevance"] == "RELEVANT"),
        "partially": sum(1 for r in results if r["relevance"] == "PARTIALLY"),
        "not_relevant": sum(1 for r in results if r["relevance"] == "NOT_RELEVANT"),
        "failed": 0
    }
    
    print(f"\ntranslated note,translated note: {model}")
    print(f"translated note: {topic}")
    print("-" * 60)
    
    with tqdm(total=len(articles_to_process), desc="translated note") as pbar:
        for i, article in enumerate(articles_to_process):
            result = process_article(
                article=article,
                agent=agent,
                topic=topic,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature
            )
            
            if result:
                # translated note
                if result.confidence < min_confidence:
                    result.relevance = "UNCERTAIN"
                
                results.append(result.__dict__)
                stats["processed"] += 1
                
                if result.relevance == "RELEVANT":
                    stats["relevant"] += 1
                elif result.relevance == "PARTIALLY":
                    stats["partially"] += 1
                elif result.relevance == "NOT_RELEVANT":
                    stats["not_relevant"] += 1
            else:
                stats["failed"] += 1
            
            pbar.update(1)
            
            # translated note
            if (i + 1) % save_interval == 0:
                save_results(output_file, results, topic, model, stats)
                pbar.set_postfix({
                    "translated note": stats["relevant"],
                    "translated note": stats["partially"],
                    "translated note": stats["not_relevant"]
                })
            
            # translated note
            time.sleep(0.1)
    
    # translated note
    save_results(output_file, results, topic, model, stats)
    
    # translated note
    print("\n" + "=" * 60)
    print("translated note!")
    print("=" * 60)
    print(f"translated note: {stats['processed']}/{stats['total']}")
    print(f"  translated note (RELEVANT): {stats['relevant']}")
    print(f"  translated note (PARTIALLY): {stats['partially']}")
    print(f"  translated note (NOT_RELEVANT): {stats['not_relevant']}")
    print(f"  translated note: {stats['failed']}")
    print(f"\ntranslated note: {output_file}")
    
    return stats


def save_results(output_file: Path, results: List[Dict], topic: str, model: str, stats: Dict):
    """translated note"""
    output_data = {
        "topic": topic,
        "model": model,
        "generated_at": datetime.now().isoformat(),
        "stats": stats,
        "results": results
    }
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)


def export_filtered_articles(
    relevance_file: Path,
    original_file: Path,
    output_file: Path,
    min_relevance: str = "RELEVANT"
) -> int:
    """
    translated note
    
    Args:
        relevance_file: translated note
        original_file: translated note all_articles.json
        output_file: translated note
        min_relevance: translated note (RELEVANT, PARTIALLY, NOT_RELEVANT)
        
    Returns:
        translated note
    """
    # translated note
    with open(relevance_file, "r", encoding="utf-8") as f:
        relevance_data = json.load(f)
    
    # translated note
    relevance_levels = ["RELEVANT"]
    if min_relevance in ["PARTIALLY", "NOT_RELEVANT"]:
        relevance_levels.append("PARTIALLY")
    if min_relevance == "NOT_RELEVANT":
        relevance_levels.append("NOT_RELEVANT")
    
    relevant_pmids = {
        r["pmid"] for r in relevance_data["results"]
        if r["relevance"] in relevance_levels
    }
    
    # translated note
    with open(original_file, "r", encoding="utf-8") as f:
        original_data = json.load(f)
    
    # translated note
    filtered_articles = [
        a for a in original_data["articles"]
        if a["pmid"] in relevant_pmids
    ]
    
    # translated note
    relevance_map = {r["pmid"]: r for r in relevance_data["results"]}
    for article in filtered_articles:
        pmid = article["pmid"]
        if pmid in relevance_map:
            article["relevance_judgment"] = {
                "relevance": relevance_map[pmid]["relevance"],
                "confidence": relevance_map[pmid]["confidence"],
                "reason": relevance_map[pmid]["reason"]
            }
    
    # translated note
    output_data = {
        "total": len(filtered_articles),
        "filter_criteria": {
            "min_relevance": min_relevance,
            "topic": relevance_data.get("topic", ""),
            "model": relevance_data.get("model", "")
        },
        "articles": filtered_articles
    }
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"translated note {len(filtered_articles)} translated note: {output_file}")
    return len(filtered_articles)


def main():
    parser = argparse.ArgumentParser(description="translated note")
    parser.add_argument("--input", type=Path, default=Path("data/metadata/all_articles.json"),
                        help="translated note")
    parser.add_argument("--output", type=Path, default=Path("data/metadata/relevance_results.json"),
                        help="translated note")
    parser.add_argument("--topic", type=str, required=True,
                        help="translated note")
    parser.add_argument("--system-prompt", type=str,
                        help="translated note")
    parser.add_argument("--model", type=str, default="minimax-m2.7",
                        help="translated note")
    parser.add_argument("--temperature", type=float, default=0.1,
                        help="translated note")
    parser.add_argument("--batch-size", type=int, default=100,
                        help="translated note")
    parser.add_argument("--save-interval", type=int, default=10,
                        help="translated note")
    parser.add_argument("--min-confidence", type=float, default=0.0,
                        help="translated note")
    parser.add_argument("--no-resume", action="store_true",
                        help="translated note,translated note")
    parser.add_argument("--export", type=Path,
                        help="translated note")
    parser.add_argument("--min-relevance", type=str, default="RELEVANT",
                        choices=["RELEVANT", "PARTIALLY", "NOT_RELEVANT"],
                        help="translated note")
    
    args = parser.parse_args()
    
    # translated note
    system_prompt = None
    if args.system_prompt:
        with open(args.system_prompt, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    
    # translated note
    stats = filter_articles(
        input_file=args.input,
        output_file=args.output,
        topic=args.topic,
        system_prompt=system_prompt,
        model=args.model,
        temperature=args.temperature,
        batch_size=args.batch_size,
        save_interval=args.save_interval,
        min_confidence=args.min_confidence,
        resume=not args.no_resume
    )
    
    # translated note
    if args.export:
        export_filtered_articles(
            relevance_file=args.output,
            original_file=args.input,
            output_file=args.export,
            min_relevance=args.min_relevance
        )


if __name__ == "__main__":
    main()
