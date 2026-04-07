"""Build the skill registry from config."""

from __future__ import annotations

from loguru import logger

from boris.config import Config
from boris.skills.base import SkillRegistry


def build_registry(config: Config) -> SkillRegistry:
    """Create and populate the skill registry based on config."""
    registry = SkillRegistry()

    # Import and register skills conditionally
    from boris.skills.reminders import ReminderSkill, RemindersListSkill

    registry.register(ReminderSkill())
    registry.register(RemindersListSkill())

    if config.skills.search.url:
        from boris.skills.search import SearchSkill

        registry.register(SearchSkill(config.skills.search.url))

    logger.info(f"Skills registradas: {registry.list_names()}")
    return registry
