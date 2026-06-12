"""Tests for boris.core.context module."""

from boris.config import Config
from boris.core.context import PERSONALITY, build_system_prompt, build_tool_schema
from boris.skills.base import Skill, SkillRegistry, SkillResult


class FakeToolSkill(Skill):
    name = "fake_tool"
    description = "Hace algo de mentira."
    args_doc = "thing (str)"

    async def execute(self, **kwargs) -> SkillResult:
        return SkillResult(ok=True, message="ok")


class NoArgsSkill(Skill):
    name = "no_args"
    description = "No necesita argumentos."

    async def execute(self, **kwargs) -> SkillResult:
        return SkillResult(ok=True, message="ok")


def _registry(*skills: Skill) -> SkillRegistry:
    registry = SkillRegistry()
    for skill in skills:
        registry.register(skill)
    return registry


def test_system_prompt_contains_personality():
    cfg = Config()
    prompt = build_system_prompt(cfg)
    assert "Boris" in prompt
    assert "mi señor" in prompt
    assert "5000 años" in prompt
    assert "mayordomo" in prompt


def test_system_prompt_contains_registered_tools():
    cfg = Config()
    prompt = build_system_prompt(cfg, registry=_registry(FakeToolSkill(), NoArgsSkill()))
    assert '"tool"' in prompt
    assert "fake_tool" in prompt
    assert "no_args" in prompt


def test_system_prompt_omits_unregistered_tools():
    cfg = Config()
    prompt = build_system_prompt(cfg, registry=_registry(FakeToolSkill()))
    assert "no_args" not in prompt


def test_system_prompt_without_registry_has_no_tool_block():
    cfg = Config()
    prompt = build_system_prompt(cfg)
    assert '"tool"' not in prompt
    assert "Herramientas disponibles" not in prompt


def test_system_prompt_with_empty_registry_has_no_tool_block():
    cfg = Config()
    prompt = build_system_prompt(cfg, registry=SkillRegistry())
    assert '"tool"' not in prompt
    assert "Herramientas disponibles" not in prompt


def test_tool_schema_renders_args_and_no_args():
    schema = build_tool_schema(_registry(FakeToolSkill(), NoArgsSkill()))
    assert "- fake_tool: Hace algo de mentira. Args: thing (str)." in schema
    assert "- no_args: No necesita argumentos. Sin args." in schema


def test_tool_schema_reflects_config_driven_registry():
    """With no credentials configured, optional skills must not be advertised."""
    from boris.skills.registry import build_registry

    cfg = Config()  # default secrets are empty
    cfg.skills.search.url = ""
    schema = build_tool_schema(build_registry(cfg))
    assert "reminder" in schema
    assert "reminders_list" in schema
    for absent in ("home", "music_play", "music_control", "calendar", "garmin", "search"):
        assert f"- {absent}:" not in schema


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
