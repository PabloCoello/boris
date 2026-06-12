"""Skill base class, result type, and registry."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass

from loguru import logger


@dataclass
class SkillResult:
    ok: bool
    message: str


class Skill(ABC):
    """Base class for all Boris skills."""

    name: str = ""
    description: str = ""
    args_doc: str = ""  # human-readable args spec for the LLM tool schema; empty = no args
    timeout_s: float = 5.0  # per-skill budget; raise for skills with slow auth flows

    @abstractmethod
    async def execute(self, **kwargs) -> SkillResult:
        ...

    async def run(self, timeout: float | None = None, **kwargs) -> SkillResult:
        """Execute with timeout and error handling.

        An explicit timeout overrides the skill's own timeout_s.
        """
        timeout = self.timeout_s if timeout is None else timeout
        try:
            return await asyncio.wait_for(self.execute(**kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Skill '{self.name}' timeout ({timeout}s)")
            return SkillResult(ok=False, message=f"Timeout: {self.name} tardó más de {timeout}s.")
        except Exception as e:
            logger.error(f"Skill '{self.name}' error: {e}")
            return SkillResult(ok=False, message=f"Error en {self.name}: {e}")


class SkillRegistry:
    """Registry of available skills, keyed by name."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill):
        self._skills[skill.name] = skill
        logger.debug(f"Skill registrada: {skill.name}")

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_names(self) -> list[str]:
        return list(self._skills.keys())

    def all(self) -> list[Skill]:
        """Return all skills in registration order."""
        return list(self._skills.values())
