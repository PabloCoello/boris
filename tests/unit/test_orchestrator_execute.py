"""Tests for skill execution in the orchestrator."""


import pytest

from boris.core.orchestrator import execute_tool_call
from boris.skills.base import Skill, SkillRegistry, SkillResult


class EchoSkill(Skill):
    name = "echo"
    description = "Echoes args."

    async def execute(self, **kwargs) -> SkillResult:
        return SkillResult(ok=True, message=f"Echo: {kwargs}")


@pytest.fixture
def registry():
    reg = SkillRegistry()
    reg.register(EchoSkill())
    return reg


@pytest.mark.asyncio
async def test_execute_known_tool(registry):
    tool_call = {"tool": "echo", "args": {"text": "hola"}}
    result = await execute_tool_call(tool_call, registry)
    assert result.ok is True
    assert "hola" in result.message


@pytest.mark.asyncio
async def test_execute_unknown_tool(registry):
    tool_call = {"tool": "nonexistent", "args": {}}
    result = await execute_tool_call(tool_call, registry)
    assert result.ok is False
    assert "no conozco" in result.message.lower() or "desconoc" in result.message.lower()


@pytest.mark.asyncio
async def test_execute_with_no_args(registry):
    tool_call = {"tool": "echo"}
    result = await execute_tool_call(tool_call, registry)
    assert result.ok is True


@pytest.mark.asyncio
async def test_execute_returns_skill_result_type(registry):
    tool_call = {"tool": "echo", "args": {"x": 1}}
    result = await execute_tool_call(tool_call, registry)
    assert isinstance(result, SkillResult)


@pytest.mark.asyncio
async def test_execute_with_non_dict_args(registry):
    tool_call = {"tool": "echo", "args": ["not", "a", "dict"]}
    result = await execute_tool_call(tool_call, registry)
    assert result.ok is False
    assert "inválidos" in result.message.lower()


@pytest.mark.asyncio
async def test_execute_with_null_args(registry):
    tool_call = {"tool": "echo", "args": None}
    result = await execute_tool_call(tool_call, registry)
    assert result.ok is True


@pytest.mark.asyncio
async def test_execute_strips_reserved_timeout_arg(registry):
    tool_call = {"tool": "echo", "args": {"timeout": "mañana", "text": "hola"}}
    result = await execute_tool_call(tool_call, registry)
    assert result.ok is True
    assert "timeout" not in result.message


@pytest.mark.asyncio
async def test_execute_respects_skill_timeout():
    import asyncio

    class SlowTool(Skill):
        name = "slow_tool"
        description = "Tarda demasiado."
        timeout_s = 0.05

        async def execute(self, **kwargs) -> SkillResult:
            await asyncio.sleep(10)
            return SkillResult(ok=True, message="nunca llega")

    reg = SkillRegistry()
    reg.register(SlowTool())
    result = await execute_tool_call({"tool": "slow_tool", "args": {}}, reg)
    assert result.ok is False
    assert "timeout" in result.message.lower()
