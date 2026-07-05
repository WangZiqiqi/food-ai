#!/usr/bin/env python3
"""
translated note - translated note claims
translated note: python vector_search.py "yogurt effect on diabetes" [--top_k 5]
"""

import os
import sys
import json
import argparse
import numpy as np
import re
from pathlib import Path
from typing import List, Tuple
from dotenv import load_dotenv
import requests

from kg_utils import data_store

# translated note
load_dotenv()


def get_embedding(text: str) -> List[float]:
    """translated note SiliconFlow API translated note embedding"""
    api_key = os.getenv("SILICONFLOW_API_KEY")
    api_url = os.getenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1/embeddings")
    model = os.getenv("SILICONFLOW_MODEL", "BAAI/bge-m3")

    if not api_key:
        raise RuntimeError("SILICONFLOW_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "input": text,
        "encoding_format": "float"
    }

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"embedding request failed: {exc}") from exc

    return result["data"][0]["embedding"]


def tokenize(text: str) -> List[str]:
    normalized = re.sub(r"[_+\-/()]+", " ", text.lower())
    return re.findall(r"[a-z0-9]+", normalized)


def lexical_similarity(query: str, text: str) -> float:
    query_tokens = tokenize(query)
    text_tokens = tokenize(text)
    if not query_tokens or not text_tokens:
        return 0.0

    query_counts = {}
    text_counts = {}
    for token in query_tokens:
        query_counts[token] = query_counts.get(token, 0) + 1
    for token in text_tokens:
        text_counts[token] = text_counts.get(token, 0) + 1

    overlap = 0.0
    for token, q_count in query_counts.items():
        overlap += min(q_count, text_counts.get(token, 0))

    norm = (sum(v * v for v in query_counts.values()) ** 0.5) * (sum(v * v for v in text_counts.values()) ** 0.5)
    if norm == 0:
        return 0.0

    substring_bonus = 0.15 if " ".join(query_tokens) in text.lower() else 0.0
    return min(overlap / norm + substring_bonus, 1.0)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """translated note"""
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


def search_claims(query: str, top_k: int = 5, mode: str = "auto") -> Tuple[List[Tuple[str, str, float]], str]:
    """
    V3: translated note claims

    Returns:
        List of (claim_id, claim_text, similarity_score)
    """
    # translated note embeddings
    try:
        data = data_store.get_embeddings()
    except FileNotFoundError as e:
        print(json.dumps({
            "error": str(e),
            "hint": "Run scripts/build_claim_embeddings_v3.py first to generate V3 embeddings"
        }, indent=2))
        sys.exit(1)

    # V3: translated note claim_ids,translated note claim_keys
    claim_ids = data.get("claim_ids", data.get("claim_keys", []))
    claim_texts = data["claim_texts"]
    embeddings = data["embeddings"]

    similarities = []
    mode_used = mode

    if mode in {"auto", "embedding"}:
        try:
            query_embedding = get_embedding(query)
            for i, emb in enumerate(embeddings):
                sim = cosine_similarity(query_embedding, emb)
                similarities.append((claim_ids[i], claim_texts[i], sim))
            mode_used = "embedding"
        except Exception:
            if mode == "embedding":
                raise

    if not similarities:
        for i, text in enumerate(claim_texts):
            sim = lexical_similarity(query, text)
            similarities.append((claim_ids[i], text, sim))
        mode_used = "lexical_fallback"

    # translated note top_k
    similarities.sort(key=lambda x: x[2], reverse=True)
    return similarities[:top_k], mode_used


def main():
    parser = argparse.ArgumentParser(description="Vector search for claims")
    parser.add_argument("query", help="Search query in natural language")
    parser.add_argument("--top_k", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument(
        "--mode",
        choices=["auto", "embedding", "lexical"],
        default="auto",
        help="Search mode: embedding, lexical, or auto fallback (default: auto)",
    )
    args = parser.parse_args()

    try:
        results, mode_used = search_claims(args.query, args.top_k, args.mode)

        # translated note JSON translated note (V3: translated note claim_id)
        output = {
            "query": args.query,
            "top_k": args.top_k,
            "search_mode": mode_used,
            "results": [
                {
                    "claim_id": cid,
                    "claim_text": text[:200] + "..." if len(text) > 200 else text,
                    "similarity": round(sim, 4)
                }
                for cid, text, sim in results
            ]
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "query": args.query,
            "search_mode": args.mode,
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
