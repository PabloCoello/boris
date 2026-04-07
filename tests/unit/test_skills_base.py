"""Tests for boris.skills.base module."""

import asyncio

import pytest

from boris.skills.base import Skill, SkillRegistry, SkillResult


class FakeSkill(Skill):
    name = "fake"
    description = "A fake skill for testing."

    async def execute(self, **kwargs) -> SkillResult:
        return SkillResult(ok=True, message=f"Got: {kwargs}")


class SlowSkill(Skill):
    name = "slow"
    description = "Simulates a slow skill."

    async def execute(self, **kwargs) -> SkillResult:
        await asyncio.sleep(10)
        return SkillResult(ok=True, message="Done")


class FailSkill(Skill):
    name = "fail"
    description = "Always fails."

    async def execute(self, **kwargs) -> SkillResult:
        raise ConnectionError("Service down")


def test_skill_result_ok():
    r = SkillResult(ok=True, message="Done")
    assert r.ok is True
    assert r.message == "Done"


def test_skill_result_error():
    r = SkillResult(ok=False, message="Error")
    assert r.ok is False


def test_registry_register_and_get():
    registry = SkillRegistry()
    skill = FakeSkill()
    registry.register(skill)
    assert registry.get("fake") is skill


def test_registry_get_unknown():
    registry = SkillRegistry()
    assert registry.get("nonexistent") is None


def test_registry_list_skills():
    registry = SkillRegistry()
    registry.register(FakeSkill())
    registry.register(SlowSkill())
    names = registry.list_names()
    assert "fake" in names
    assert "slow" in names


@pytest.mark.asyncio
async def test_execute_skill():
    skill = FakeSkill()
    result = await skill.run(greeting="hello", timeout=5.0)
    assert result.ok is True
    assert "hello" in result.message


@pytest.mark.asyncio
async def test_timeout_returns_error():
    skill = SlowSkill()
    result = await skill.run(timeout=0.1)
    assert result.ok is False
    assert "timeout" in result.message.lower()


@pytest.mark.asyncio
async def test_exception_returns_error():
    skill = FailSkill()
    result = await skill.run(timeout=5.0)
    assert result.ok is False
    assert "Service down" in result.message
