#!/usr/bin/env python3
"""Build document-level title+abstract embeddings for raw PubMed RAG baselines."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("SILICONFLOW_API_KEY")
API_URL = os.getenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1/embeddings")
MODEL = os.getenv("SILICONFLOW_MODEL", "BAAI/bge-m3")

DEFAULT_CORPUS = Path("data/processed/selected_850_quality_llm_abstract_complete_2026-04-26.json")
DEFAULT_OUTPUT = Path("data/processed/final_graph/abstract_embeddings_bge_m3.json")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def article_text(article: dict[str, Any]) -> str:
    title = str(article.get("title") or "").strip()
    abstract = str(article.get("abstract") or "").strip()
    return f"{title}\n\n{abstract}".strip()


def load_articles(path: Path) -> list[dict[str, Any]]:
    data = load_json(path)
    articles = data.get("articles", data if isinstance(data, list) else [])
    if not isinstance(articles, list):
        raise ValueError(f"Could not find article list in {path}")
    return [article for article in articles if article.get("pmid") and article_text(article)]


def get_embeddings_batch(
    texts: list[str],
    batch_size: int,
    max_retries: int,
    timeout: int,
) -> list[list[float]]:
    if not API_KEY:
        raise RuntimeError("SILICONFLOW_API_KEY not set")

    all_embeddings = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        print(
            f"  embedding batch {start // batch_size + 1}/{(len(texts)-1)//batch_size + 1} ({len(batch)})",
            flush=True,
        )
        payload = {
            "model": MODEL,
            "input": batch,
            "encoding_format": "float",
        }
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    API_URL,
                    headers={
                        "Authorization": f"Bearer {API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()
                result = response.json()
                break
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= max_retries:
                    raise
                sleep_seconds = min(2**attempt, 10)
                print(f"    retry {attempt}/{max_retries}: {exc}", flush=True)
                time.sleep(sleep_seconds)
        else:
            raise RuntimeError(f"embedding request failed: {last_error}")

        all_embeddings.extend(item["embedding"] for item in result["data"])
        time.sleep(0.1)
    return all_embeddings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()

    articles = load_articles(args.corpus)
    pmids = [str(article["pmid"]) for article in articles]
    titles = [str(article.get("title") or "") for article in articles]
    abstracts = [str(article.get("abstract") or "") for article in articles]
    texts = [article_text(article) for article in articles]

    print(f"Loaded {len(texts)} articles from {args.corpus}")
    embeddings = get_embeddings_batch(texts, args.batch_size, args.max_retries, args.timeout)

    payload = {
        "version": "document_abstract_v1",
        "model": MODEL,
        "source_corpus": str(args.corpus),
        "total_articles": len(pmids),
        "pmids": pmids,
        "titles": titles,
        "abstracts": abstracts,
        "texts": texts,
        "embeddings": embeddings,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(embeddings)} abstract embeddings to {args.output}")


if __name__ == "__main__":
    main()
