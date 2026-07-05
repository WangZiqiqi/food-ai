#!/usr/bin/env python3
"""
Shared Claude Agent SDK runtime helpers for the Food-AI agent entrypoints.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


DEFAULT_STREAM_CLOSE_TIMEOUT_MS = "600000"
DEFAULT_HOOK_TIMEOUT_SECONDS = 600
CURRENT_KG_PATH = "data/processed/final_graph/food_ai_graph.pkl"
CURRENT_EMBEDDINGS_PATH = "data/processed/final_graph/claim_embeddings_bge_m3.json"


def configure_sdk_environment(project_root: Path) -> str:
    """
    Load the project .env file and configure the SDK transport environment.
    """
    load_dotenv(project_root / ".env")

    os.environ["CLAUDECODE"] = "0"
    os.environ.setdefault(
        "CLAUDE_CODE_STREAM_CLOSE_TIMEOUT", DEFAULT_STREAM_CLOSE_TIMEOUT_MS
    )

    settings_override = os.environ.get("FOOD_AI_AGENT_SETTINGS")
    if settings_override:
        model = (
            os.environ.get("FOOD_AI_AGENT_MODEL")
            or os.environ.get("ANTHROPIC_MODEL")
            or "kimi-k2-5"
        )
        os.environ["ANTHROPIC_MODEL"] = model
        os.environ["ANTHROPIC_DEFAULT_SONNET_MODEL"] = os.environ.get(
            "ANTHROPIC_DEFAULT_SONNET_MODEL", model
        )
        os.environ["ANTHROPIC_DEFAULT_OPUS_MODEL"] = os.environ.get(
            "ANTHROPIC_DEFAULT_OPUS_MODEL", model
        )
        os.environ["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = os.environ.get(
            "ANTHROPIC_DEFAULT_HAIKU_MODEL", model
        )
        configure_graph_environment(project_root)
        return os.environ.get("ANTHROPIC_AUTH_TOKEN", "")

    anthropic_base_url = os.environ.get("ANTHROPIC_BASE_URL")
    anthropic_auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")

    # Prefer the Claude SDK / Anthropic-compatible variables directly. This
    # supports Poe-hosted Kimi without carrying the old api.kimi.com/coding
    # defaults into new runs. Keep KIMI_* as a legacy fallback for existing .envs.
    if not anthropic_base_url:
        anthropic_base_url = os.environ.get("KIMI_API_URL", "http://127.0.0.1:3456")
    if not anthropic_auth_token:
        anthropic_auth_token = os.environ.get("KIMI_API_KEY", "")
    if not anthropic_auth_token:
        raise RuntimeError(
            "ANTHROPIC_AUTH_TOKEN or KIMI_API_KEY not set. "
            "For Poe Kimi, set ANTHROPIC_BASE_URL=https://api.poe.com, "
            "ANTHROPIC_AUTH_TOKEN, and ANTHROPIC_MODEL=kimi-k2.5."
        )

    model = (
        os.environ.get("ANTHROPIC_MODEL")
        or os.environ.get("KIMI_MODEL")
        or "kimi-k2.5"
    )

    os.environ["ANTHROPIC_BASE_URL"] = anthropic_base_url
    os.environ["ANTHROPIC_AUTH_TOKEN"] = anthropic_auth_token
    os.environ["ANTHROPIC_MODEL"] = model
    os.environ["ANTHROPIC_DEFAULT_SONNET_MODEL"] = os.environ.get(
        "ANTHROPIC_DEFAULT_SONNET_MODEL", model
    )
    os.environ["ANTHROPIC_DEFAULT_OPUS_MODEL"] = os.environ.get(
        "ANTHROPIC_DEFAULT_OPUS_MODEL", model
    )
    os.environ["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = os.environ.get(
        "ANTHROPIC_DEFAULT_HAIKU_MODEL", model
    )
    configure_graph_environment(project_root)
    return anthropic_auth_token


def configure_graph_environment(project_root: Path) -> None:
    graph_candidates = [
        (CURRENT_KG_PATH, CURRENT_EMBEDDINGS_PATH),
    ]
    for kg_relative_path, embeddings_relative_path in graph_candidates:
        kg_path = project_root / kg_relative_path
        if not kg_path.exists():
            continue
        os.environ.setdefault("FOOD_AI_KG_PICKLE_PATH", str(kg_path))
        os.environ.setdefault("FOOD_AI_REFINER_KG_PATH", str(kg_path))
        if embeddings_relative_path:
                embeddings_path = project_root / embeddings_relative_path
                if embeddings_path.exists():
                    os.environ.setdefault("FOOD_AI_EMBEDDINGS_PATH", str(embeddings_path))
        break


def create_debug_options(enabled: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Build SDK hook/stderr callbacks so we can inspect tool activity when needed.
    """
    state: dict[str, Any] = {
        "session_id": None,
        "transcript_paths": [],
        "tool_events": [],
        "stderr": [],
        "stream_events": [],
    }
    if not enabled:
        return {}, state

    from claude_agent_sdk import HookMatcher

    async def hook_cb(
        input_data: dict[str, Any], tool_result: str | None, context: Any
    ) -> dict[str, Any]:
        event = input_data.get("hook_event_name", "unknown")
        session_id = input_data.get("session_id")
        transcript_path = input_data.get("transcript_path")
        if session_id and not state["session_id"]:
            state["session_id"] = session_id
        if transcript_path and transcript_path not in state["transcript_paths"]:
            state["transcript_paths"].append(transcript_path)

        record = {
            "event": event,
            "session_id": session_id,
            "tool_name": input_data.get("tool_name"),
            "tool_use_id": input_data.get("tool_use_id"),
            "tool_input": input_data.get("tool_input"),
            "error": input_data.get("error"),
            "transcript_path": transcript_path,
        }
        state["tool_events"].append(record)
        print(
            f"[sdk:{event}] {json.dumps(record, ensure_ascii=False, default=str)}",
            flush=True,
        )
        return {"hookEventName": event}

    def stderr_cb(text: str) -> None:
        text = text.rstrip("\n")
        if not text:
            return
        state["stderr"].append(text)
        print(f"[sdk:stderr] {text}", flush=True)

    options = {
        "include_partial_messages": True,
        "stderr": stderr_cb,
        "hooks": {
            "PreToolUse": [HookMatcher(hooks=[hook_cb], timeout=DEFAULT_HOOK_TIMEOUT_SECONDS)],
            "PostToolUse": [HookMatcher(hooks=[hook_cb], timeout=DEFAULT_HOOK_TIMEOUT_SECONDS)],
            "PostToolUseFailure": [
                HookMatcher(hooks=[hook_cb], timeout=DEFAULT_HOOK_TIMEOUT_SECONDS)
            ],
            "Stop": [HookMatcher(hooks=[hook_cb], timeout=DEFAULT_HOOK_TIMEOUT_SECONDS)],
            "Notification": [HookMatcher(hooks=[hook_cb], timeout=DEFAULT_HOOK_TIMEOUT_SECONDS)],
        },
    }
    return options, state


def extract_text_and_tool_calls(event: Any) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Collect readable text and tool-use blocks from SDK message events.
    """
    texts: list[str] = []
    tool_calls: list[dict[str, Any]] = []

    result = getattr(event, "result", None)
    if result is None and isinstance(event, dict):
        result = event.get("result")
    if isinstance(result, str):
        texts.append(result)

    content: Any = None
    for candidate in (event, getattr(event, "message", None)):
        if candidate is None:
            continue
        candidate_content = getattr(candidate, "content", None)
        if candidate_content is None and isinstance(candidate, dict):
            candidate_content = candidate.get("content")
        if isinstance(candidate_content, list):
            content = candidate_content
            break

    if not isinstance(content, list):
        return texts, tool_calls

    for item in content:
        item_type = getattr(item, "type", None)
        if item_type is None and isinstance(item, dict):
            item_type = item.get("type")
        item_class = type(item).__name__

        if item_type == "text" or item_class == "TextBlock":
            text = getattr(item, "text", None)
            if text is None and isinstance(item, dict):
                text = item.get("text")
            if isinstance(text, str):
                texts.append(text)
        elif item_type == "tool_use" or item_class == "ToolUseBlock":
            if isinstance(item, dict):
                tool_calls.append(
                    {
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "input": item.get("input"),
                    }
                )
            else:
                tool_calls.append(
                    {
                        "id": getattr(item, "id", None),
                        "name": getattr(item, "name", None),
                        "input": getattr(item, "input", None),
                    }
                )
        elif item_class == "ToolResultBlock":
            tool_calls.append(
                {
                    "id": getattr(item, "tool_use_id", None) if not isinstance(item, dict) else item.get("tool_use_id"),
                    "name": "tool_result",
                    "input": getattr(item, "content", None) if not isinstance(item, dict) else item.get("content"),
                }
            )

    return texts, tool_calls


def log_stream_event(
    event: Any,
    texts: list[str],
    tool_calls: list[dict[str, Any]],
    state: dict[str, Any] | None = None,
) -> None:
    """
    Print a compact view of SDK stream events so long-running calls are observable.
    """
    event_type = type(event).__name__
    summary = {
        "event_type": event_type,
        "text_blocks": len(texts),
        "tool_calls": len(tool_calls),
    }

    message = getattr(event, "message", None)
    if message is not None:
        role = getattr(message, "role", None)
        if role:
            summary["role"] = role

    if state is not None:
        state.setdefault("stream_events", []).append(summary)

    print(
        f"[sdk:event] {json.dumps(summary, ensure_ascii=False, default=str)}",
        flush=True,
    )

    for text in texts:
        snippet = " ".join(text.split())
        if len(snippet) > 240:
            snippet = snippet[:240] + "..."
        print(
            f"[sdk:text:{event_type}] {snippet}",
            flush=True,
        )

    for tool_call in tool_calls:
        tool_summary = {
            "id": tool_call.get("id"),
            "name": tool_call.get("name"),
            "input": tool_call.get("input"),
        }
        print(
            f"[sdk:tool_call] {json.dumps(tool_summary, ensure_ascii=False, default=str)}",
            flush=True,
        )
