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

    @abstractmethod
    async def execute(self, **kwargs) -> SkillResult:
        ...

    async def run(self, timeout: float = 5.0, **kwargs) -> SkillResult:
        """Execute with timeout and error handling."""
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
