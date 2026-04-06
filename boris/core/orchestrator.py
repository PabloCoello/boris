"""Tool call dispatcher — parses LLM JSON responses and routes to skills."""

from __future__ import annotations

import json

from loguru import logger


def parse_tool_call(response: str) -> tuple[dict | None, str]:
    """Parse LLM response for tool calls.

    The spec contract says: "No mezcles texto y JSON en la misma respuesta."
    So we try to parse the full response as JSON first. If it's valid JSON
    with a "tool" key, it's a tool call. Otherwise, it's plain text.

    Returns (tool_call_dict, spoken_text).
    - If response is a valid tool call JSON: ({"tool": ..., "args": ...}, "")
    - If response is plain text: (None, response)
    """
    stripped = response.strip()

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict) and "tool" in parsed:
            logger.info(f"Tool call detectado: {parsed['tool']}")
            return parsed, ""
    except (json.JSONDecodeError, ValueError):
        pass

    return None, response
