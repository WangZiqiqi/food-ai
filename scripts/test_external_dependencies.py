#!/usr/bin/env python3
"""
Test network reachability and minimal API requests for external dependencies.
"""

from __future__ import annotations

import json
import os
import socket
import time
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()


def mask(value: str | None) -> str:
    if not value:
        return "missing"
    if len(value) <= 8:
        return "***present***"
    return f"{value[:4]}...{value[-4:]}"


def dns_check(host: str) -> dict:
    started = time.time()
    try:
        addrs = sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
        return {
            "ok": True,
            "host": host,
            "addresses": addrs[:5],
            "elapsed_ms": round((time.time() - started) * 1000, 1),
        }
    except Exception as exc:
        return {
            "ok": False,
            "host": host,
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_ms": round((time.time() - started) * 1000, 1),
        }


def http_request(name: str, method: str, url: str, **kwargs) -> dict:
    started = time.time()
    try:
        response = requests.request(method, url, timeout=20, **kwargs)
        preview = response.text[:300]
        return {
            "name": name,
            "ok": response.ok,
            "status_code": response.status_code,
            "elapsed_ms": round((time.time() - started) * 1000, 1),
            "response_preview": preview,
        }
    except Exception as exc:
        return {
            "name": name,
            "ok": False,
            "elapsed_ms": round((time.time() - started) * 1000, 1),
            "error": f"{type(exc).__name__}: {exc}",
        }


def test_poe() -> dict:
    api_key = os.getenv("POE_API_KEY")
    api_url = os.getenv("POE_API_URL", "https://api.poe.com/v1/chat/completions")
    payload = {
        "model": os.getenv("POE_MODEL", "minimax-m2.7"),
        "messages": [{"role": "user", "content": "Reply with exactly: pong"}],
        "temperature": 0,
        "max_tokens": 8,
    }
    return http_request(
        "poe_chat_completion",
        "POST",
        api_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
    )


def test_siliconflow() -> dict:
    api_key = os.getenv("SILICONFLOW_API_KEY")
    api_url = os.getenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1/embeddings")
    payload = {
        "model": os.getenv("SILICONFLOW_MODEL", "BAAI/bge-m3"),
        "input": "network connectivity test",
        "encoding_format": "float",
    }
    return http_request(
        "siliconflow_embeddings",
        "POST",
        api_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
    )


def test_ncbi() -> dict:
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    return http_request(
        "ncbi_esearch",
        "GET",
        base_url,
        params={"db": "pubmed", "term": "yogurt diabetes", "retmax": 1, "retmode": "json"},
    )


def test_kimi_base() -> dict:
    url = os.getenv("KIMI_API_URL", "https://api.kimi.com/coding/")
    return http_request("kimi_base", "GET", url, headers={"Authorization": f"Bearer {os.getenv('KIMI_API_KEY', '')}"})


def main() -> int:
    poe_url = os.getenv("POE_API_URL", "https://api.poe.com/v1/chat/completions")
    siliconflow_url = os.getenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1/embeddings")
    kimi_url = os.getenv("KIMI_API_URL", "https://api.kimi.com/coding/")

    hosts = {
        "poe": urlparse(poe_url).hostname,
        "siliconflow": urlparse(siliconflow_url).hostname,
        "kimi": urlparse(kimi_url).hostname,
        "ncbi": "eutils.ncbi.nlm.nih.gov",
    }

    report = {
        "env": {
            "POE_API_KEY": mask(os.getenv("POE_API_KEY")),
            "POE_API_URL": poe_url,
            "SILICONFLOW_API_KEY": mask(os.getenv("SILICONFLOW_API_KEY")),
            "SILICONFLOW_API_URL": siliconflow_url,
            "KIMI_API_KEY": mask(os.getenv("KIMI_API_KEY")),
            "KIMI_API_URL": kimi_url,
        },
        "dns": {name: dns_check(host) for name, host in hosts.items() if host},
        "http": {
            "ncbi": test_ncbi(),
            "poe": test_poe(),
            "siliconflow": test_siliconflow(),
            "kimi": test_kimi_base(),
        },
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
