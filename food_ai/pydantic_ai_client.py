"""Shared pydantic-ai model helpers for Poe/OpenAI-compatible LLM calls."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

load_dotenv()


def create_poe_model(model_name: str | None = None) -> OpenAIChatModel:
    """Create a pydantic-ai OpenAI-compatible model backed by Poe by default."""
    api_key = os.getenv("POE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("translated note POE_API_KEY translated note OPENAI_API_KEY translated note")

    base_url = (
        os.getenv("POE_API_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    )
    provider = OpenAIProvider(
        base_url=base_url.replace("/chat/completions", ""),
        api_key=api_key,
    )
    return OpenAIChatModel(
        model_name=model_name or os.getenv("POE_MODEL", "minimax-m2.7"),
        provider=provider,
    )
