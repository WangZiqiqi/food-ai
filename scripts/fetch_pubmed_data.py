#!/usr/bin/env python3
"""
translated note PubMed translated note

translated note:
    python scripts/fetch_pubmed_data.py "yogurt probiotic diabetes" --max-results 10 --output data/raw/pubmed_results.json
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# translated note
sys.path.insert(0, str(Path(__file__).parent.parent))


def search_pubmed(query: str, max_results: int = 10) -> List[str]:
    """
    translated note PubMed skill translated note,translated note PMID translated note
    """
    import subprocess
    
    skill_path = Path(__file__).parent.parent.parent / "skills" / "pubmed" / "scripts" / "pubmed_search.py"
    
    cmd = [
        "python3", str(skill_path),
        "search", query,
        "--max-results", str(max_results)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"translated note: {result.stderr}")
        return []
    
    try:
        data = json.loads(result.stdout)
        articles = data.get("articles", [])
        return [a.get("pmid") for a in articles if a.get("pmid")]
    except json.JSONDecodeError as e:
        print(f"translated note: {e}")
        return []


def fetch_article_details(pmids: List[str]) -> List[Dict[str, Any]]:
    """
    translated note(translated note)
    """
    import subprocess
    
    skill_path = Path(__file__).parent.parent.parent / "skills" / "pubmed" / "scripts" / "pubmed_search.py"
    
    articles = []
    for pmid in pmids:
        print(f"  translated note PMID {pmid} translated note...")
        
        cmd = [
            "python3", str(skill_path),
            "abstract", pmid,
            "--metadata"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"    ✗ translated note: {result.stderr}")
            continue
        
        try:
            article_data = json.loads(result.stdout)
            articles.append(article_data)
            print(f"    ✓ translated note")
        except json.JSONDecodeError as e:
            print(f"    ✗ translated note: {e}")
            continue
    
    return articles


def main():
    parser = argparse.ArgumentParser(description="translated note PubMed translated note")
    parser.add_argument("query", help="PubMed translated note")
    parser.add_argument("--max-results", type=int, default=10, help="translated note")
    parser.add_argument("--output", "-o", required=True, help="translated note JSON translated note")
    
    args = parser.parse_args()
    
    print(f"translated note: {args.query}")
    print(f"translated note: {args.max_results}")
    print("-" * 50)
    
    # translated note
    print("\n1. translated note...")
    pmids = search_pubmed(args.query, args.max_results)
    
    if not pmids:
        print("translated note")
        return 1
    
    print(f"translated note {len(pmids)} translated note")
    
    # translated note
    print(f"\n2. translated note...")
    articles = fetch_article_details(pmids)
    
    print(f"\ntranslated note {len(articles)} translated note")
    
    # translated note
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    result_data = {
        "query": args.query,
        "total_found": len(pmids),
        "total_fetched": len(articles),
        "articles": articles
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\ntranslated note: {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
