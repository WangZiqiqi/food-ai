#!/usr/bin/env python3
"""
Minimal Claude Agent SDK probe for transport / hook / tool-call debugging.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from sdk_runtime import (
    configure_sdk_environment,
    create_debug_options,
    extract_text_and_tool_calls,
    log_stream_event,
)


PROJECT_ROOT = Path(__file__).parent.parent.resolve()

try:
    configure_sdk_environment(PROJECT_ROOT)
except RuntimeError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    sys.exit(1)


def build_prompt(use_bash: bool) -> str:
    if not use_bash:
        return (
            "Reply with exactly one short sentence: "
            "'sdk probe text response ok'. Do not use any tools."
        )
    return """Use the Bash tool exactly once.

Run this command:
`pwd`

Then reply with one short sentence describing the working directory.
Do not use any other tools."""


async def run_probe(timeout_seconds: int, use_bash: bool, enable_hooks: bool) -> dict[str, Any]:
    try:
        from claude_agent_sdk import ClaudeAgentOptions, query
    except ImportError as exc:
        return {"success": False, "error": f"Cannot import claude_agent_sdk: {exc}"}

    debug_options, debug_state = create_debug_options(enable_hooks)
    prompt = build_prompt(use_bash)

    options = ClaudeAgentOptions(
        cwd=str(PROJECT_ROOT),
        permission_mode="bypassPermissions",
        max_turns=4,
        settings=str(Path(os.environ["FOOD_AI_AGENT_SETTINGS"]).expanduser())
        if os.environ.get("FOOD_AI_AGENT_SETTINGS")
        else None,
        model=os.environ.get("FOOD_AI_AGENT_MODEL") or os.environ.get("ANTHROPIC_MODEL"),
        **debug_options,
    )

    full_response: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    event_counts: dict[str, int] = {}

    try:
        async with asyncio.timeout(timeout_seconds):
            response_stream = query(prompt=prompt, options=options)
            async for event in response_stream:
                event_type = type(event).__name__
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
                texts, event_tool_calls = extract_text_and_tool_calls(event)
                log_stream_event(event, texts, event_tool_calls, debug_state)
                full_response.extend(texts)
                tool_calls.extend(event_tool_calls)
    except TimeoutError:
        return {
            "success": False,
            "timeout": True,
            "error": f"Timed out after {timeout_seconds}s",
            "agent_response": "".join(full_response),
            "tool_calls": tool_calls,
            "event_counts": event_counts,
            "session_id": debug_state.get("session_id"),
            "transcript_paths": debug_state.get("transcript_paths", []),
            "stream_events": debug_state.get("stream_events", []),
            "stderr": debug_state.get("stderr", []),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "agent_response": "".join(full_response),
            "tool_calls": tool_calls,
            "event_counts": event_counts,
            "session_id": debug_state.get("session_id"),
            "transcript_paths": debug_state.get("transcript_paths", []),
            "stream_events": debug_state.get("stream_events", []),
            "stderr": debug_state.get("stderr", []),
        }

    return {
        "success": True,
        "agent_response": "".join(full_response),
        "tool_calls": tool_calls,
        "event_counts": event_counts,
        "session_id": debug_state.get("session_id"),
        "transcript_paths": debug_state.get("transcript_paths", []),
        "stream_events": debug_state.get("stream_events", []),
        "stderr": debug_state.get("stderr", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal Claude Agent SDK probe")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    parser.add_argument(
        "--mode",
        choices=["text", "bash"],
        default="bash",
        help="Whether to require a Bash tool call",
    )
    parser.add_argument(
        "--hooks",
        action="store_true",
        help="Enable SDK debug hooks (PreToolUse/PostToolUse/etc)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Claude Agent SDK Minimal Probe")
    print("=" * 70)
    print(f"cwd: {PROJECT_ROOT}")
    print(f"mode: {args.mode}")
    print(f"hooks: {args.hooks}")
    print(f"timeout: {args.timeout}s")

    result = asyncio.run(
        run_probe(
            timeout_seconds=args.timeout,
            use_bash=args.mode == "bash",
            enable_hooks=args.hooks,
        )
    )

    print("\nResult:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
