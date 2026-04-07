"""Tool call dispatcher — parses LLM JSON responses and routes to skills."""

from __future__ import annotations

import json

from loguru import logger

from boris.skills.base import SkillRegistry, SkillResult

SKILL_TIMEOUT = 5.0


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


async def execute_tool_call(tool_call: dict, registry: SkillRegistry) -> SkillResult:
    """Execute a parsed tool call against the skill registry."""
    tool_name = tool_call.get("tool", "")
    tool_args = tool_call.get("args", {})

    skill = registry.get(tool_name)
    if skill is None:
        logger.warning(f"Tool desconocida: {tool_name}")
        return SkillResult(ok=False, message=f"No conozco la acción '{tool_name}'.")

    logger.info(f"Ejecutando skill: {tool_name}({tool_args})")
    return await skill.run(timeout=SKILL_TIMEOUT, **tool_args)
