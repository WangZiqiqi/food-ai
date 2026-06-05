#!/usr/bin/env python3
"""Small sequential PubMed E-utilities rate smoke test."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "skills" / "pubmed" / "scripts"))

import pubmed_search  # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser(description="Sequentially test PubMed API access through the local rate limiter")
    parser.add_argument("--calls", type=int, default=3, help="Number of search calls; each search makes ESearch + EFetch")
    parser.add_argument("--query", default='((yogurt[Title] OR kefir[Title]) AND Randomized Controlled Trial[Publication Type])')
    parser.add_argument("--max-results", type=int, default=1)
    args = parser.parse_args()

    results = []
    started = time.monotonic()
    for index in range(max(1, args.calls)):
        call_started = time.monotonic()
        response = pubmed_search.search_pubmed(
            args.query,
            max_results=args.max_results,
            start_index=index * args.max_results,
            sort_order="relevance",
        )
        results.append(
            {
                "call": index + 1,
                "elapsed_seconds": round(time.monotonic() - call_started, 3),
                "count": response.get("count"),
                "returned": len(response.get("articles", [])),
                "pmids": [article.get("pmid") for article in response.get("articles", [])],
            }
        )

    total_elapsed = time.monotonic() - started
    eutility_requests = len(results) * 2
    print(
        json.dumps(
            {
                "ok": True,
                "calls": len(results),
                "eutility_requests": eutility_requests,
                "configured_min_interval_seconds": pubmed_search.get_min_interval(),
                "elapsed_seconds": round(total_elapsed, 3),
                "observed_eutility_rps": round(eutility_requests / total_elapsed, 3) if total_elapsed else None,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
