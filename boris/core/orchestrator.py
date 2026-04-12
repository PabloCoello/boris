"""Tool call dispatcher — parses LLM JSON responses and routes to skills."""

from __future__ import annotations

import json

from loguru import logger

from boris.skills.base import SkillRegistry, SkillResult

SKILL_TIMEOUT = 5.0


def parse_tool_call(response: str) -> tuple[dict | None, str]:
    """Parse LLM response for tool calls.

    The spec contract says: "No mezcles texto y JSON en la misma respuesta."
    So we try to parse the full response as JSON first. If that fails,
    look for a JSON object embedded in the text (LLM sometimes mixes
    prose and JSON despite instructions).

    Returns (tool_call_dict, spoken_text).
    - If response is a valid tool call JSON: ({"tool": ..., "args": ...}, "")
    - If JSON is embedded in text: ({"tool": ..., "args": ...}, surrounding_text)
    - If response is plain text: (None, response)
    """
    stripped = response.strip()

    # Case 1: entire response is a tool call JSON
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict) and "tool" in parsed:
            logger.info(f"Tool call detectado: {parsed['tool']}")
            return parsed, ""
    except (json.JSONDecodeError, ValueError):
        pass

    # Case 2: JSON embedded in text (e.g. "Some text\n{"tool": ...}\nMore text")
    brace_start = stripped.find("{")
    if brace_start != -1:
        brace_end = stripped.rfind("}")
        if brace_end > brace_start:
            candidate = stripped[brace_start : brace_end + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict) and "tool" in parsed:
                    text_before = stripped[:brace_start].strip()
                    text_after = stripped[brace_end + 1 :].strip()
                    spoken = " ".join(p for p in (text_before, text_after) if p)
                    logger.info(f"Tool call detectado (embedded): {parsed['tool']}")
                    return parsed, spoken
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
