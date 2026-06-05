"""
Lightweight embedding client for build-time entity canonicalization.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()


class EmbeddingClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        self.api_url = api_url or os.getenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1/embeddings")
        self.model = model or os.getenv("SILICONFLOW_MODEL", "BAAI/bge-m3")
        self.timeout = timeout
        self.max_retries = max_retries
        self._cache: dict[str, list[float]] = {}

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def embed(self, text: str) -> list[float]:
        text = (text or "").strip()
        if not text:
            return []
        if text in self._cache:
            return self._cache[text]
        if not self.enabled:
            return []

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "input": [text],
                        "encoding_format": "float",
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                self._cache[text] = embedding
                return embedding
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        print(f"    Warning: Embedding failed for '{text[:40]}': {str(last_error)[:80]}")
        return []


_default_client: Optional[EmbeddingClient] = None


def get_embedding_client() -> EmbeddingClient:
    global _default_client
    if _default_client is None:
        _default_client = EmbeddingClient()
    return _default_client
