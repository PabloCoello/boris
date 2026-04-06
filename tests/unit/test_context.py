"""Tests for boris.core.context module."""

from boris.config import Config
from boris.core.context import PERSONALITY, TOOL_SCHEMA, build_system_prompt


def test_system_prompt_contains_personality():
    cfg = Config()
    prompt = build_system_prompt(cfg)
    assert "Boris" in prompt
    assert "mi señor" in prompt
    assert "5000 años" in prompt
    assert "mayordomo" in prompt


def test_system_prompt_contains_tool_schema():
    cfg = Config()
    prompt = build_system_prompt(cfg)
    assert '"tool"' in prompt
    assert "reminder" in prompt
    assert "garmin" in prompt
    assert "home" in prompt
    assert "music_play" in prompt


def test_system_prompt_with_memory():
    cfg = Config()
    memory = "El señor prefiere el café sin azúcar."
    prompt = build_system_prompt(cfg, memory_context=memory)
    assert "café sin azúcar" in prompt
    assert "Contexto de memoria" in prompt


def test_system_prompt_without_memory():
    cfg = Config()
    prompt = build_system_prompt(cfg, memory_context=None)
    assert "Contexto de memoria" not in prompt


def test_personality_is_in_spanish():
    assert "español" in PERSONALITY.lower()


def test_tool_schema_has_all_tools():
    tools = ["home", "reminder", "reminders_list", "calendar", "music_play", "music_control", "search", "garmin"]
    for tool in tools:
        assert tool in TOOL_SCHEMA
