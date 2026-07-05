#!/usr/bin/env python3
"""
translated note V3 translated note Claim translated note
translated note extraction_v3.json translated note merged_claims
"""

import os
import json
import requests
import numpy as np
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
import time

load_dotenv()

API_KEY = os.getenv("SILICONFLOW_API_KEY")
API_URL = os.getenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1/embeddings")
MODEL = os.getenv("SILICONFLOW_MODEL", "BAAI/bge-m3")

V3_PATH = Path("data/processed/final_graph/food_ai_graph.json")
OUTPUT_PATH = Path("data/processed/final_graph/claim_embeddings_bge_m3.json")


def get_embeddings_batch(
    texts: List[str],
    batch_size: int = 16,
    max_retries: int = 3,
    timeout: int = 60,
) -> List[List[float]]:
    """translated note embedding"""
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"  translated note {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1} ({len(batch)} translated note)")

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": MODEL,
            "input": batch,
            "encoding_format": "float"
        }

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(API_URL, headers=headers, json=data, timeout=timeout)
                response.raise_for_status()
                result = response.json()
                break
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= max_retries:
                    raise
                sleep_seconds = min(2 ** attempt, 10)
                print(f"    Warning: embedding translated note,translated note {attempt}/{max_retries}: {exc}")
                time.sleep(sleep_seconds)
        else:
            raise RuntimeError(f"embedding translated note: {last_error}")

        batch_embeddings = [item["embedding"] for item in result["data"]]
        all_embeddings.extend(batch_embeddings)

        time.sleep(0.1)

    return all_embeddings


def claim_to_text(claim: Dict) -> str:
    """V3: translated note claim translated note"""
    subject = claim.get("subject_name", "")
    obj = claim.get("object_name", "")
    direction = claim.get("direction", "")

    # V3 claim_text translated note
    claim_text = claim.get("claim_text", "")
    if claim_text:
        return claim_text

    # translated note:translated note
    text = f"{subject} has {direction} effect on {obj}"
    return text


def main():
    import argparse
    parser = argparse.ArgumentParser(description='translated noteClaimtranslated note')
    parser.add_argument('--input', type=str, default=str(V3_PATH), help='translated note')
    parser.add_argument('--output', type=str, default=str(OUTPUT_PATH), help='translated noteembeddingtranslated note')
    parser.add_argument('--batch-size', type=int, default=16, help='translated note embedding translated note')
    parser.add_argument('--max-retries', type=int, default=5, help='translated note')
    parser.add_argument('--timeout', type=int, default=90, help='translated note(translated note)')
    args = parser.parse_args()

    print("📚 translated note V3 translated note...")
    with open(args.input, 'r') as f:
        v3_data = json.load(f)

    # V3: translated note merged_claims
    claims = v3_data.get("merged_claims", [])

    print(f"   translated note {len(claims)} translated note merged claims")

    # translated note
    print("\n📝 translated note claim translated note...")
    claim_ids = []
    claim_texts = []

    for claim in claims:
        claim_id = claim.get("claim_id")
        if not claim_id:
            continue

        text = claim_to_text(claim)
        claim_ids.append(claim_id)
        claim_texts.append(text)

    # translated note
    print("\n   translated note:")
    for i in range(min(3, len(claim_texts))):
        print(f"   {i+1}. {claim_texts[i][:150]}...")

    # translated note embedding
    print(f"\n🔢 translated note embedding ({MODEL})...")
    start_time = time.time()
    embeddings = get_embeddings_batch(
        claim_texts,
        batch_size=args.batch_size,
        max_retries=args.max_retries,
        timeout=args.timeout,
    )
    elapsed = time.time() - start_time
    print(f"   ✓ translated note！translated note {elapsed:.2f} translated note")
    print(f"   translated note: {len(embeddings[0])}")

    # translated note
    print("\n💾 translated note embedding...")
    embedding_data = {
        "model": MODEL,
        "claim_ids": claim_ids,  # V3: translated note claim_id translated note claim_key
        "claim_texts": claim_texts,
        "embeddings": embeddings,
        "total_claims": len(claim_ids),
        "version": "v3"
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(embedding_data, f)

    print(f"   ✓ translated note {output_path}")

    # translated note
    print("\n translated note...")
    test_queries = [
        "yogurt effect on diabetes",
        "probiotic improves blood sugar",
        "kefir and cholesterol"
    ]

    def cosine_similarity(vec1, vec2):
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    for query in test_queries:
        print(f"\n   translated note: \"{query}\"")
        query_emb = get_embeddings_batch(
            [query],
            batch_size=1,
            max_retries=args.max_retries,
            timeout=args.timeout,
        )[0]

        similarities = []
        for i, emb in enumerate(embeddings):
            sim = cosine_similarity(query_emb, emb)
            similarities.append((claim_ids[i], claim_texts[i], sim))

        similarities.sort(key=lambda x: x[2], reverse=True)

        for i, (cid, text, sim) in enumerate(similarities[:3], 1):
            print(f"   {i}. [translated note: {sim:.4f}] {text[:80]}...")

    print("\n V3 translated note！")


if __name__ == "__main__":
    main()
